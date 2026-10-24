"""Combine browser structure and desktop evidence when both adapters are enabled."""
async def observe_computer(browser=None, desktop=None):
    observation = {**await browser.snapshot(), **await browser.screenshot()} if browser else {}
    if desktop:
        observation['browser_screenshot'] = observation.get('screenshot')
        observation.update(await desktop.screenshot())
    return observation or {'observer': 'unconfigured', 'screenshot': None}
