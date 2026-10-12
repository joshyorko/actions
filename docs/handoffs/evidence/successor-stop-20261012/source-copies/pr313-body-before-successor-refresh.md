Captured-child cleanup could return while an originally captured descendant was still alive, although the shared deadline still had time left. After the exclusive Popen wait, cleanup now waits only for those identity-bound live descendants using the remaining same deadline. It preserves inspection/wait errors and final live/zombie classification; it adds no signals, PID lookup, second Popen wait or deadline extension.

Validation: deterministic asynchronous-exit and wait-error controls failed before the change and pass after it. All ten permanent controls pass. Configured Runtime source gate: 1,305 passed, 13 existing skips, two workers. Independent LIGHT and full source reviews passed; all 1,422 typed source leaves, original evidence, prepared environments and native/helper originals are retained.

This is a source-qualified cleanup correction in the existing #133/#134/#139/#143 → #221 graph. The hosted Windows failure's causal relationship remains unknown. Current hosted CI, real OS cleanup, new RCC/source/fixture combinations and Runtime 1.0.3 publication still require their own acceptance. No release gate is waived.

Source `499a83d802ca9a0e2ebe3d77071af10625879297`, tree `e13ba51b094e429b7c06d6dabbbcc348cc66e86c`, parent/base `a0d258a16095b95b1bf9000cb1201cddfaff4779`.
