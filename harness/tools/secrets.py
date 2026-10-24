"""Secrets are inserted directly into a browser field and never returned."""
import os


class SecretTools:
    def __init__(self, browser, redactor=None, service='computer-harness'):
        self.browser, self.redactor, self.service = browser, redactor, service

    async def insert(self, name: str, ref: str, sequential: bool = False):
        if not name or not name.replace('_', '').isalnum():
            raise ValueError('Secret name must be an environment-key identifier')
        value = os.environ.get(name)
        if value is None:
            import keyring
            value = keyring.get_password(self.service, name)
        if value is None:
            raise ValueError('Requested secret is not configured')
        if self.redactor:
            self.redactor.register(value)
        self.browser.register_secret(value)
        if sequential:
            await self.browser.type(ref, value, sequential=True)
        else:
            await self.browser.type(ref, value)
        return {'inserted': True}
