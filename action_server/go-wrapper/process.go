package main

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"syscall"
)

// runChild forwards wrapper-directed POSIX SIGTERM and reaps the same child.
// SIGINT keeps its existing foreground process-group behavior.
func runChild(cmd *exec.Cmd) error {
	if runtime.GOOS == "windows" {
		return cmd.Run()
	}

	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGTERM)
	defer signal.Stop(signals)

	if err := cmd.Start(); err != nil {
		return err
	}
	waited := make(chan error, 1)
	go func() { waited <- cmd.Wait() }()
	for {
		select {
		case err := <-waited:
			return err
		case received := <-signals:
			if err := cmd.Process.Signal(received); err != nil && !errors.Is(err, os.ErrProcessDone) {
				fmt.Fprintf(os.Stderr, "Error forwarding %s to child process: %s\n", received, err)
			}
		}
	}
}
