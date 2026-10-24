from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv


def flag(name, default=False):
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes'}


@dataclass
class Settings:
    data_dir: Path
    skills_dir: Path
    host: str = '127.0.0.1'
    port: int = 8787
    password: str = ''
    allowed_hosts: tuple = ('localhost', '127.0.0.1', '[::1]')
    cookie_secure: bool = False
    timezone: str = 'Asia/Kolkata'
    internal_url: str = 'http://127.0.0.1:8787'
    browser_mode: str = 'managed'
    browser_headless: bool = True
    browser_channel: str = ''
    cdp_url: str = ''
    browser_hosts: tuple = ('localhost', '127.0.0.1', '::1')
    desktop_enabled: bool = False
    max_steps: int = 100
    max_seconds: int = 300
    provider: str = 'claude'
    skill_writes_enabled: bool = True
    freeze_manifest: str = ''
    triggers_file: str = ''
    telegram_enabled: bool = False
    telegram_chat_id: str = ''

    @classmethod
    def from_env(cls, env_file='.env'):
        load_dotenv(env_file, override=False)
        return cls(Path(os.getenv('DATA_DIR', './data')).resolve(),
                   Path(os.getenv('SKILLS_DIR', './skills')).resolve(),
                   host=os.getenv('HOST','127.0.0.1'), port=int(os.getenv('PORT',8787)),
                   password=os.getenv('GUI_PASSWORD',''),
                   allowed_hosts=tuple(x.strip() for x in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1,[::1]').split(',') if x.strip()),
                   cookie_secure=flag('COOKIE_SECURE'), timezone=os.getenv('TIMEZONE','Asia/Kolkata'),
                   internal_url=os.getenv('INTERNAL_URL','http://127.0.0.1:'+os.getenv('PORT','8787')),
                   browser_mode=os.getenv('BROWSER_MODE','managed'), browser_headless=flag('BROWSER_HEADLESS',True),
                   browser_channel=os.getenv('BROWSER_CHANNEL',''),
                   cdp_url=os.getenv('CDP_URL',''),
                   browser_hosts=tuple(x.strip() for x in os.getenv('BROWSER_ALLOWED_HOSTS','localhost,127.0.0.1,::1').split(',') if x.strip()),
                   desktop_enabled=flag('DESKTOP_ENABLED'), max_steps=int(os.getenv('MAX_STEPS',100)),
                   max_seconds=int(os.getenv('MAX_SECONDS',300)), provider=os.getenv('LLM_PROVIDER','claude'),
                   skill_writes_enabled=flag('SKILL_WRITES_ENABLED', True), freeze_manifest=os.getenv('FREEZE_MANIFEST', ''),
                   triggers_file=os.getenv('TRIGGERS_FILE', ''), telegram_enabled=flag('TELEGRAM_ENABLED'),
                   telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID', ''))

    def validate(self):
        from zoneinfo import ZoneInfo
        ZoneInfo(self.timezone)
        if self.host not in {'127.0.0.1', 'localhost', '::1'} and len(self.password) < 12:
            raise ValueError('Set GUI_PASSWORD to at least 12 characters before exposing the server')
        if self.browser_mode not in {'managed','cdp','none'}:
            raise ValueError('BROWSER_MODE must be managed, cdp or none')
        if self.provider not in {'claude','deepseek'}:
            raise ValueError('LLM_PROVIDER must be claude or deepseek')

    def providers(self):
        return {
            'claude': {'base_url':os.getenv('CLAUDE_BASE_URL','https://api.anthropic.com/v1'),
                       'model':os.getenv('CLAUDE_MODEL','claude-haiku-4-5-20251001'), 'key_env':'ANTHROPIC_API_KEY',
                       'protocol':'messages','vision':True,'timeout':30},
            'deepseek': {'base_url':os.getenv('DEEPSEEK_BASE_URL','https://api.deepseek.com'),
                         'model':os.getenv('DEEPSEEK_MODEL','deepseek-flash'), 'key_env':'DEEPSEEK_API_KEY',
                         'protocol':'chat','vision':flag('DEEPSEEK_VISION',True),'timeout':30}}

    def available(self):
        return {name:{'model':p['model'],'configured':bool(os.getenv(p['key_env'])),'vision':p['vision']}
                for name,p in self.providers().items()}

    def runtime(self, provider=None, demo=False):
        provider=provider or self.provider
        if provider not in self.providers():
            raise ValueError('Unknown model provider')
        selected=self.providers()[provider]
        models=[] if demo else [selected]
        if not demo and not os.getenv(selected['key_env']):
            raise ValueError(f"Add {selected['key_env']} to the server .env and restart")
        for name,p in self.providers().items():
            if not demo and name!=provider and os.getenv(p['key_env']): models.append(p)
        return {'runs':str(self.data_dir/'runs'), 'workspace':str(self.data_dir/'workspace'),
                'skills':str(self.skills_dir), 'learned_skills':str(self.data_dir/'skills'), 'models':models,
                'skill_writes_enabled':self.skill_writes_enabled and not bool(self.freeze_manifest),
                'freeze_manifest':self.freeze_manifest,
                'max_steps':self.max_steps,'max_seconds':self.max_seconds,
                'browser':{'mode':self.browser_mode, 'cdp_url':self.cdp_url,
                           'headless':self.browser_headless,
                           'channel':self.browser_channel or None,
                           'profile_dir':str(self.data_dir/('demo-browser-profile' if demo else 'browser-profile')),
                           'allowed_hosts':list(self.browser_hosts)},
                'desktop':{'enabled':self.desktop_enabled and not demo}}
