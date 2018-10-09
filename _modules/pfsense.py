import json, logging, os, subprocess

__virtualname__ = 'pfsense'
__PFCLI__ = '/usr/local/bin/php-cgi'
oscmd = subprocess.Popen
PIPE = subprocess.PIPE
DEFAULT_PFSENSE_INCLUDES = [
    'globals.inc',
    'functions.inc',
    'config.inc',
    'util.inc'
    ]

def __virtual__():
    '''
    only load if pfsense CLI is available
    '''
    if os.access('/usr/local/sbin/pfSsh.php', os.X_OK):
        IS_PFSENSE = __virtualname__
    else:
        IS_PFSENSE = False
    return IS_PFSENSE

class Script():
    '''
    attributes:
      includes: list of PHP "require_once" include files
      body: list of script lines as strings

    str():
      conversion to string rendes the the script with includes, in PHP tags
    '''
    includes = []
    body = []
    def __init__(self, *args, **kwargs):
        if args:
            for arg in args:
                if len(self.body) > 0:
                    self.body.append('')
                self.body += arg.splitlines()
            if 'includes' in kwargs:
                for inc in kwargs['includes']:
                    self.includes.append(inc)
            else:
                self.includes = DEFAULT_PFSENSE_INCLUDES

    def __str__(self):
        PHP_begin = "<?php\n"
        PHP_end = "\n?>"

        _fmt_inc_ = 'require_once("{}");'
        includes_block = "\n".join([_fmt_inc_.format(i) for i in self.includes])
        script_body = "\n".join(self.body)
        return PHP_begin + includes_block + script_body + PHP_end

def run(script):
    '''
    runs a script via pfSense php-cgi CLI and returns a tuple:
      - stdout
      - stderr
    '''
    log = logging.getLogger(__virtualname__ + '.' + __name__)
    shell = oscmd([__PFCLI__], stdin=PIPE, stdout=PIPE, stderr=PIPE)

    log.debug("running commands in php-cgi: \n%s", str(script))
    raw_out, raw_err = shell.communicate(input=str(script))
    if raw_out:
        log.debug("stdout:\n%s", raw_out)
    if raw_err:
        log.debug("stderr:\n%s", raw_err)

    if raw_out[:13].lower() == 'content-type:': # strip bogus MIME header
        out = '\n'.join(raw_out.splitlines()[1:])
    return out, raw_err


def get_config(*args):
    '''
    Optionally takes a string argument as colon-delimited config key:
      - if the key is not truth-y (Default None), the whole config is returned
      - if the key is not found in the config, None is returned
      - if the key is found, the matching part of the config is returned

    uses php-cgi CLI to run PHP commands
    returns the pfSense $config nested array structure as native python data

    PHP -> json -> python
    '''
    key = None
    if len(args) > 1 or (len(args) == 1 and args[0] != str(args[0])):
        raise ValueError('get_config optionally takes only 1 string argument as key')
    else:
        if len(args) == 1:
            key = args[0].split(':')
    log = logging.getLogger(__virtualname__ + '.' + __name__)
    __dump_config_php__ = 'print_r(json_encode($config, $options=JSON_PRETTY_PRINT));'
    get_config_script = Script(__dump_config_php__)
    cmd_out, cmd_err = run(get_config_script)
    pfConfig = json.loads(cmd_out)

    if key: # iteratively prune the config for the key or return None
        for i in key:
            ctx_pfConfig = pfConfig
            if i in ctx_pfConfig:
                pfConfig = ctx_pfConfig[i]
            else:
                pfConfig = None
                break

    return pfConfig
