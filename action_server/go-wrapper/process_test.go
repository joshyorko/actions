package main

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"syscall"
	"testing"
	"time"
)

const fixtureRole = "ACTIONS_GO_WRAPPER_TEST_ROLE"

func fixtureCommand(role string) *exec.Cmd {
	cmd := exec.Command(os.Args[0], "-test.run=^TestRunChildFixture$")
	for _, entry := range os.Environ() {
		if !strings.HasPrefix(entry, fixtureRole+"=") {
			cmd.Env = append(cmd.Env, entry)
		}
	}
	cmd.Env = append(cmd.Env, fixtureRole+"="+role)
	return cmd
}

func TestRunChildFixture(t *testing.T) {
	switch os.Getenv(fixtureRole) {
	case "exit":
		os.Exit(23)
	case "child":
		signals := make(chan os.Signal, 1)
		signal.Notify(signals, syscall.SIGTERM)
		fmt.Printf("ready %d\n", os.Getpid())
		<-signals
		fmt.Println("received")
		<-signals
		fmt.Println("received-again")
		release, err := bufio.NewReader(os.Stdin).ReadString('\n')
		if err != nil || release != "release\n" {
			os.Exit(4)
		}
		fmt.Println("cleaned")
		os.Exit(23)
	case "wrapper":
		cmd := fixtureCommand("child")
		cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
		err := runChild(cmd)
		fmt.Println("reaped")
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			os.Exit(exitErr.ExitCode())
		}
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	case "launch-failed", "natural-reaped":
		cmd := fixtureCommand("exit")
		if os.Getenv(fixtureRole) == "launch-failed" {
			cmd = exec.Command(os.Getenv("ACTIONS_GO_WRAPPER_TEST_MISSING_EXECUTABLE"))
		}
		if err := runChild(cmd); err == nil {
			os.Exit(4)
		}
		fmt.Println("finished")
		_, _ = bufio.NewReader(os.Stdin).ReadString('\n')
		os.Exit(4)
	}
}

func readFixtureLine(t *testing.T, reader *bufio.Reader) string {
	t.Helper()
	line := make(chan string, 1)
	go func() {
		value, _ := reader.ReadString('\n')
		line <- strings.TrimSpace(value)
	}()
	select {
	case value := <-line:
		return value
	case <-time.After(5 * time.Second):
		t.Fatal("fixture did not respond within five seconds")
		return ""
	}
}

func startFixture(t *testing.T, role string, stdin *os.File) (*exec.Cmd, *bufio.Reader, chan error) {
	t.Helper()
	cmd := fixtureCommand(role)
	if role == "launch-failed" {
		cmd.Env = append(cmd.Env, "ACTIONS_GO_WRAPPER_TEST_MISSING_EXECUTABLE="+filepath.Join(t.TempDir(), "missing-executable"))
	}
	cmd.Stdin = stdin
	cmd.Stderr = os.Stderr
	stdout, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	cmd.Stdout = writer
	if err := cmd.Start(); err != nil {
		_ = writer.Close()
		_ = stdout.Close()
		t.Fatal(err)
	}
	_ = writer.Close()
	t.Cleanup(func() {
		_ = cmd.Process.Kill()
		_ = stdout.Close()
	})
	waited := make(chan error, 1)
	go func() { waited <- cmd.Wait() }()
	return cmd, bufio.NewReader(stdout), waited
}

func TestRunChildForwardsSIGTERMAndReaps(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("requires POSIX SIGTERM")
	}
	stdin, writer, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	// Keep the wrapper's input open until the child's cleanup is released.
	cmd, reader, waited := startFixture(t, "wrapper", stdin)
	t.Cleanup(func() {
		_ = stdin.Close()
		_ = writer.Close()
	})
	var childPID int
	if _, err := fmt.Sscanf(readFixtureLine(t, reader), "ready %d", &childPID); err != nil {
		t.Fatal(err)
	}
	child, err := os.FindProcess(childPID)
	if err != nil {
		t.Fatal(err)
	}
	childReaped := false
	t.Cleanup(func() {
		if !childReaped {
			_ = child.Kill()
		}
		_ = child.Release()
	})
	if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
		t.Fatal(err)
	}
	if received := readFixtureLine(t, reader); received != "received" {
		t.Fatalf("child did not receive SIGTERM: %q", received)
	}
	select {
	case err := <-waited:
		t.Fatalf("wrapper exited before child cleanup: %v", err)
	default:
	}
	if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
		t.Fatal(err)
	}
	if received := readFixtureLine(t, reader); received != "received-again" {
		t.Fatalf("child did not receive the second SIGTERM: %q", received)
	}
	if _, err := fmt.Fprintln(writer, "release"); err != nil {
		t.Fatal(err)
	}
	if cleaned := readFixtureLine(t, reader); cleaned != "cleaned" {
		t.Fatalf("child did not finish cleanup: %q", cleaned)
	}
	if reaped := readFixtureLine(t, reader); reaped != "reaped" {
		t.Fatalf("wrapper did not reap child: %q", reaped)
	}
	select {
	case err := <-waited:
		var exitErr *exec.ExitError
		if !errors.As(err, &exitErr) || exitErr.ExitCode() != 23 {
			t.Fatalf("wrapper did not preserve child exit code 23: %v", err)
		}
		childReaped = true
	case <-time.After(5 * time.Second):
		t.Fatal("wrapper did not exit after child cleanup")
	}
}

func TestRunChildRestoresSIGTERMAfterReturn(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("requires POSIX SIGTERM")
	}
	for _, role := range []string{"launch-failed", "natural-reaped"} {
		t.Run(role, func(t *testing.T) {
			stdin, writer, err := os.Pipe()
			if err != nil {
				t.Fatal(err)
			}
			cmd, reader, waited := startFixture(t, role, stdin)
			t.Cleanup(func() {
				_ = stdin.Close()
				_ = writer.Close()
			})
			if line := readFixtureLine(t, reader); line != "finished" {
				t.Fatalf("runChild did not return: %q", line)
			}
			if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
				t.Fatal(err)
			}
			select {
			case err := <-waited:
				var exitErr *exec.ExitError
				if !errors.As(err, &exitErr) || exitErr.ExitCode() != -1 {
					t.Fatalf("SIGTERM handler was not restored: %v", err)
				}
			case <-time.After(5 * time.Second):
				t.Fatal("stale runChild handler swallowed SIGTERM")
			}
		})
	}
}

func TestRunChildLaunchFailureAndNaturalExit(t *testing.T) {
	missing := exec.Command(filepath.Join(t.TempDir(), "missing-executable"))
	err := runChild(missing)
	var exitErr *exec.ExitError
	if err == nil || errors.As(err, &exitErr) {
		t.Fatalf("expected launcher error, got %v", err)
	}
	cmd := fixtureCommand("exit")
	err = runChild(cmd)
	if !errors.As(err, &exitErr) || exitErr.ExitCode() != 23 {
		t.Fatalf("expected natural child exit code 23, got %v", err)
	}
	if cmd.ProcessState == nil || !cmd.ProcessState.Exited() {
		t.Fatal("naturally exiting child was not reaped")
	}
}
