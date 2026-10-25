# Prepared compiler Core proof diagnosis

Original manual verification remains FAILED: artifact trust attachment verification failed. No retry, build, trust-policy change, attachment edit or credential action performed. The original log does not reveal which carrier/default resolution failed, so the following is a supported invocation correction, not a proven successful fix.

Concrete divergence: RccExecutionAdapter._execute calls build_exec_command with local_trust_carrier=self.prepared.robocorp_home / "artifacts/v1/trust". The helper appends --trust-carrier PATH --trust-carrier-type filesystem. The reported manual invocation omitted these. That exact carrier exists under /workspace/actions-327-a39/compiler/robocorp/artifacts/v1/trust for ff881cb7903461ed387ab79912105aa0726e91354f8a05b01fd4f337620141d2; metadata-hashes.json records attachment names/sizes/hashes without contents. Adapter test test_rcc_runtime_adapter.py around2088 explicitly asserts both flags and retained --permissive-local.

Supported next invocation, for root review only:
Use build_exec_command from the installed candidate with RccRuntimeDescriptor(artifact_digest=prepared.artifact_digest, provider_reference="local"), command=["python","-I",absolute_verify_core_script,absolute_compiler_directory], receipt_file=fresh_receipt_path, local_trust_carrier=Path(prepared.robocorp_home)/"artifacts/v1/trust"; insert --no-build after executable exactly as adapter does. Do not remove verification or alter trust roots/revocations.

Child environment should match RccExecutionAdapter._child_environment: fresh owned HOME/ACTIONS_HOME/TMPDIR; PATH=/usr/sbin:/sbin:/bin:/usr/bin; ROBOCORP_HOME=/workspace/actions-327-a39/compiler/robocorp; LANG=LC_ALL=C.UTF-8; RCC_NO_BUILD=1. Do not inherit activate.sh's other home/config variables. Activate.sh sets ROBOCORP_HOME=/workspace/actions-cloud/robocorp and ACTIONS_HOME/ROBOTS_HOME plus XDG paths, which differ from the prepared artifact home unless explicitly replaced. The failure log alone cannot reconstruct the failed process's full environment.

Read-only --help confirms filesystem trust-carrier is supported and default selection is auto; it also emitted mkdir read-only errors for default /home/agent/.robocorp because help initialized default RCC paths. No exec retry occurred. Working ordinary Tasks reported by root are a separate acceptance result, not a pass for this failed manual probe.

Upstream disposition:none. No upstream defect demonstrated.
