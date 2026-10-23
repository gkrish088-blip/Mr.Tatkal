import os
from pathlib import Path
from harness.skillrt.loader import SkillLoader


def preflight(config):
    checks=[]
    def check(name, ok, detail): checks.append({'name':name,'ok':bool(ok),'detail':detail})
    try:
        skills=SkillLoader(config.get('skills','skills')).index()
        check('skills',bool(skills),f'{len(skills)} valid skills')
    except Exception as exc: check('skills',False,str(exc))
    models=config.get('models',[])
    check('models',bool(models),'Configure model providers for autonomous reasoning')
    for model in models:
        check('model_key:'+model['key_env'],bool(os.getenv(model['key_env'])),'Environment presence only; quota/API response not checked')
    bc=config.get('browser',{})
    check('browser',bool(bc.get('cdp_url')),'Operator must launch dedicated Chrome and verify CDP attachment')
    check('handoff',config.get('telegram',{}).get('enabled',False),'Configure and exercise the channel before live use')
    profile=config.get('profile')
    if profile:
        import yaml
        try:
            data=yaml.safe_load(Path(profile).read_text(encoding='utf-8'))
            missing=[k for k in ('name','age','gender','nationality','mobile') if not data.get(k)]
            check('profile',not missing,'Missing required fields: '+', '.join(missing) if missing else 'Required fields present')
        except Exception as exc: check('profile',False,type(exc).__name__)
    check('real_rehearsal',config.get('rehearsal_verified') is True,'Requires operator-recorded rehearsal evidence')
    return {'ok':all(c['ok'] for c in checks),'checks':checks}
