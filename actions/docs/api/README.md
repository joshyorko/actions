<!-- markdownlint-disable -->

# API Overview

## Modules

- [`actions`](./actions.md#module-actions): Sema4.ai Actions enables running your AI actions in the Sema4.ai Action Server.
- [`actions.agent`](./actions.agent.md#module-actionsagent)
- [`actions.api`](./actions.api.md#module-actionsapi): This module contains the public API for the actions.
- [`actions.chat`](./actions.chat.md#module-actionschat)
- [`actions.cli`](./actions.cli.md#module-actionscli)
- [`actions.mcp`](./actions.mcp.md#module-actionsmcp): Sema4.ai MCP (Model Context Protocol) bindings for Python.

## Classes

- [`_response.ActionError`](./actions._response.md#class-actionerror): This is a custom error which actions returning a `Response` are expected
- [`_protocols.IAction`](./actions._protocols.md#class-iaction)
- [`_secret.OAuth2Secret`](./actions._secret.md#class-oauth2secret): This class should be used to specify that OAuth2 secrets should be received.
- [`_request.Request`](./actions._request.md#class-request): Contains the information exposed in a request (such as headers and cookies).
- [`_response.Response`](./actions._response.md#class-response): The response class provides a way for the user to signal that the action
- [`_secret.Secret`](./actions._secret.md#class-secret): This class should be used to receive secrets.
- [`_secret.SecretSpec`](./actions._secret.md#class-secretspec): Metadata for secrets that specifies a tag for identification by external clients.
- [`_protocols.Status`](./actions._protocols.md#class-status): Action state
- [`_table.Table`](./actions._table.md#class-table): Table is a simple data structure that represents a table with columns and rows.
- [`_platforms.AzureOpenAIPlatformParameters`](./actions.agent._platforms.md#class-azureopenaiplatformparameters): Parameters for the Azure OpenAI platform.
- [`_platforms.BedrockPlatformParameters`](./actions.agent._platforms.md#class-bedrockplatformparameters): Parameters for the Bedrock platform.
- [`_models.ConversationHistoryParams`](./actions.agent._models.md#class-conversationhistoryparams): Parameters for the conversation history special message.
- [`_models.ConversationHistorySpecialMessage`](./actions.agent._models.md#class-conversationhistoryspecialmessage): Special message for including the conversation history in a prompt.
- [`_platforms.CortexPlatformParameters`](./actions.agent._platforms.md#class-cortexplatformparameters): Parameters for the Snowflake Cortex platform.
- [`_models.DocumentsParams`](./actions.agent._models.md#class-documentsparams): Parameters for the documents special message.
- [`_models.DocumentsSpecialMessage`](./actions.agent._models.md#class-documentsspecialmessage): Special message for including the documents in a prompt.
- [`_platforms.GooglePlatformParameters`](./actions.agent._platforms.md#class-googleplatformparameters): Parameters for the Google platform.
- [`_platforms.GroqPlatformParameters`](./actions.agent._platforms.md#class-groqplatformparameters): Parameters for the Groq platform.
- [`_models.MemoriesParams`](./actions.agent._models.md#class-memoriesparams): Parameters for the memories special message.
- [`_models.MemoriesSpecialMessage`](./actions.agent._models.md#class-memoriesspecialmessage): Special message for including the memories in a prompt.
- [`_platforms.OpenAIPlatformParameters`](./actions.agent._platforms.md#class-openaiplatformparameters): Parameters for the OpenAI platform.
- [`_models.Prompt`](./actions.agent._models.md#class-prompt): Represents a complete prompt for an AI model interaction.
- [`_models.PromptAgentMessage`](./actions.agent._models.md#class-promptagentmessage): Represents an agent message in the prompt.
- [`_models.PromptAudioContent`](./actions.agent._models.md#class-promptaudiocontent): Represents an audio message in the agent system.
- [`_models.PromptDocumentContent`](./actions.agent._models.md#class-promptdocumentcontent): Represents a document message in the agent system.
- [`_models.PromptImageContent`](./actions.agent._models.md#class-promptimagecontent): Represents an image message in the agent system.
- [`_models.PromptTextContent`](./actions.agent._models.md#class-prompttextcontent): Represents a text message in the agent system.
- [`_models.PromptToolResultContent`](./actions.agent._models.md#class-prompttoolresultcontent): Represents the result of a tool execution in the agent system.
- [`_models.PromptToolUseContent`](./actions.agent._models.md#class-prompttoolusecontent): Represents a message containing a tool use request from an AI agent.
- [`_models.PromptUserMessage`](./actions.agent._models.md#class-promptusermessage): Represents a user message in the prompt.
- [`_platforms.ReductoPlatformParameters`](./actions.agent._platforms.md#class-reductoplatformparameters): Parameters for the Reducto platform.
- [`_response.ResponseAudioContent`](./actions.agent._response.md#class-responseaudiocontent): Represents audio content generated or referenced in a model's response.
- [`_response.ResponseDocumentContent`](./actions.agent._response.md#class-responsedocumentcontent): Represents a document generated or referenced in a model's response.
- [`_response.ResponseImageContent`](./actions.agent._response.md#class-responseimagecontent): Represents an image generated or referenced in a model's response.
- [`_response.ResponseMessage`](./actions.agent._response.md#class-responsemessage): A response message from a language model hosted on a platform.
- [`_response.ResponseTextContent`](./actions.agent._response.md#class-responsetextcontent): Represents a text segment in a model's response.
- [`_response.ResponseToolUseContent`](./actions.agent._response.md#class-responsetoolusecontent): Represents a tool use request generated by the model.
- [`_response.TokenUsage`](./actions.agent._response.md#class-tokenusage): Represents token usage statistics from a model's response.
- [`_models.ToolDefinition`](./actions.agent._models.md#class-tooldefinition): Represents the definition of a tool.
- [`api.DiagnosticsTypedDict`](./actions.api.md#class-diagnosticstypeddict)
- [`api.PositionTypedDict`](./actions.api.md#class-positiontypeddict)
- [`api.RangeTypedDict`](./actions.api.md#class-rangetypeddict)

## Functions

- [`actions.action`](./actions.md#function-action): Decorator for actions (entry points) which can be executed by `actions`.
- [`actions.action_cache`](./actions.md#function-action_cache): Provides decorator which caches return and clears it automatically when the
- [`actions.get_current_action`](./actions.md#function-get_current_action): Provides the action which is being currently run or None if not currently
- [`actions.get_output_dir`](./actions.md#function-get_output_dir): Provide the output directory being used for the run or None if there's no
- [`actions.session_cache`](./actions.md#function-session_cache): Provides decorator which caches return and clears automatically when all
- [`_fixtures.setup`](./actions._fixtures.md#function-setup): Run code before any actions start, or before each separate action.
- [`_fixtures.teardown`](./actions._fixtures.md#function-teardown): Run code after actions have been run, or after each separate action.
- [`agent.get_agent_id`](./actions.agent.md#function-get_agent_id): Get the agent ID from the action context or the request headers.
- [`agent.get_data_frame`](./actions.agent.md#function-get_data_frame): Get a data frame by name from the current thread.
- [`agent.get_thread_id`](./actions.agent.md#function-get_thread_id): Get the thread ID from the action context or the request headers.
- [`agent.list_data_frames`](./actions.agent.md#function-list_data_frames): List all data frames available in the current thread.
- [`agent.prompt_generate`](./actions.agent.md#function-prompt_generate): Gives a prompt to an agent.
- [`api.collect_lint_errors`](./actions.api.md#function-collect_lint_errors): Provides lint errors from the contents of a file containing the `@action`s.
- [`chat.attach_file`](./actions.chat.md#function-attach_file): Attaches a file to the current chat.
- [`chat.attach_file_content`](./actions.chat.md#function-attach_file_content): Set the content of a file to be used in the current chat.
- [`chat.attach_json`](./actions.chat.md#function-attach_json): Attach a file with JSON content to the current chat.
- [`chat.attach_text`](./actions.chat.md#function-attach_text): Attach a file with text content to the current chat.
- [`chat.get_file`](./actions.chat.md#function-get_file): Get the content of a file in the current action chat, saves it to a temporary file
- [`chat.get_file_content`](./actions.chat.md#function-get_file_content): Get the content of a file in the current action chat.
- [`chat.get_json`](./actions.chat.md#function-get_json): Get the JSON content of a file in the current action chat.
- [`chat.get_text`](./actions.chat.md#function-get_text): Get the text content of a file in the current action chat.
- [`chat.list_files`](./actions.chat.md#function-list_files): Lists all files in the current chat thread.
- [`cli.main`](./actions.cli.md#function-main): Entry point for running actions from actions-core.
- [`mcp.prompt`](./actions.mcp.md#function-prompt): Decorator for functions that generate prompts for the LLM.
- [`mcp.resource`](./actions.mcp.md#function-resource): Decorator for resources which provide data to the LLM.
- [`mcp.tool`](./actions.mcp.md#function-tool): Decorator for tools which can be used by AI agents to perform actions.
