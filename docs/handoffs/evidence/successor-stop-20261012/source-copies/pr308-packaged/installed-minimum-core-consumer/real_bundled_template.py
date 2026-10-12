from pathlib import Path
import json,stat,hashlib
from actions.server import _settings,_oauth2_config
from actions.server._oauth2 import print_user_oauth2_config_path,USER_CONFIG_FILE_NAME
root=Path(__file__).parent/'real-private-template';root.mkdir(mode=0o700)
original=_settings.get_default_settings_dir
try:
 _settings.get_default_settings_dir=lambda:root
 assert print_user_oauth2_config_path()==0
 f=root/USER_CONFIG_FILE_NAME
 assert f.read_bytes()==_oauth2_config.FILE_CONTENTS['default_user_config'].encode()
 assert stat.S_IMODE(f.stat().st_mode)==0o600
 print(json.dumps({'real_bundled_getter':True,'template_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'mode':oct(stat.S_IMODE(f.stat().st_mode))}))
finally:_settings.get_default_settings_dir=original
