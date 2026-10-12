import pathlib,json,actions.server,actions.server._oauth2_config,importlib.metadata
root=pathlib.Path(__file__).parent.resolve()
for m in [actions.server,actions.server._oauth2_config]:
 assert pathlib.Path(m.__file__).resolve().is_relative_to(root/".venv"),m.__file__
print(json.dumps({"version":importlib.metadata.version("actions-runtime"),"runtime":actions.server.__file__,"oauth_bundle":actions.server._oauth2_config.__file__},indent=2))
