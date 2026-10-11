Give every preservation-sensitive pytest invocation its own unique, absent
`--basetemp` outside the shared numbered pytest parent, and retain policy `all`.
The installed pytest default retains three numbered roots and registers cleanup
at process exit; a later invocation can delete an earlier completed test root.
Explicit basetemp bypasses that numbered-root cleanup, but pytest removes an
existing explicit target before using it. Never reuse a retained target or share
one basetemp setting across sequential Toolkit and Runtime invocations. Policy
`none` increases deletion; it does not disable cleanup. Before attributing a
vanished root, bind recorded commands and installed cleanup source, distinguish
scratch loss from independently retained logs and source receipts, and keep
unobserved process attribution and broader evidence references unknown.
