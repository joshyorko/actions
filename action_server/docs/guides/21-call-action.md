# The Action Server provides a REST-based API based on the OpenAPI spec.

Just calling the API will allow you to use the Action Server as a tool for your AI Agents.

There are some custom ways to send data to the Action Server thought:

1. `X-Action-Invocation-Context` header (changes how the body is processed):

When this header is present, the `body` is expected to be a json where the
`body` key is the actual input to the action and any other keys are additional headers.

This header is expected to contain a data envelope (`base64(encrypted_data(JSON.stringify(content)))`
or `base64(JSON.stringify(content))`) with the invocation context, where
the invocation context should be a dict containing the following keys:

- `agent_id`
- `invoked_on_behalf_of_user_id`
- `thread_id`
- `tenant_id`
- `action_invocation_id`

2. `X-Action-Context` header:

This is a header where secrets are expected to be passed.

See: [07-secrets.md](07-secrets.md) for more details.
