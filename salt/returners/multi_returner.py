"""
Read/Write multiple returners

"""

import logging

import salt.minion

log = logging.getLogger(__name__)

CONFIG_KEY = "multi_returner"

# cache of the master mininon for this returner
MMINION = None


def _mminion():
    """
    Create a single mminion for this module to use, instead of reloading all the time
    """
    global MMINION

    if MMINION is None:
        MMINION = salt.minion.MasterMinion(__opts__)

    return MMINION


def prep_jid(nocache=False, passed_jid=None):
    """
    Call both with prep_jid on all returners in multi_returner

    TODO: finish this, what do do when you get different jids from 2 returners...
    since our jids are time based, this make this problem hard, because they
    aren't unique, meaning that we have to make sure that no one else got the jid
    and if they did we spin to get a new one, which means "locking" the jid in 2
    returners is non-trivial
    """

    jid = passed_jid
    for returner_ in __opts__[CONFIG_KEY]:
        if jid is None:
            jid = _mminion().returners[f"{returner_}.prep_jid"](nocache=nocache)
        else:
            r_jid = _mminion().returners[f"{returner_}.prep_jid"](nocache=nocache)
            if r_jid != jid:
                log.debug("Uhh.... crud the jids do not match")
    return jid


def returner(load):
    """
    Write return to all returners in multi_returner
    """
    for returner_ in __opts__[CONFIG_KEY]:
        _mminion().returners[f"{returner_}.returner"](load)


def save_load(jid, clear_load, minions=None):
    """
    Write load to all returners in multi_returner
    """
    for returner_ in __opts__[CONFIG_KEY]:
        _mminion().returners[f"{returner_}.save_load"](jid, clear_load)


def save_minions(jid, minions, syndic_id=None):  # pylint: disable=unused-argument
    """
    Included for API consistency
    """


def get_load(jid):
    """
    Merge the load data from all returners
    """
    ret = {}
    for returner_ in __opts__[CONFIG_KEY]:
        ret.update(_mminion().returners[f"{returner_}.get_load"](jid))

    return ret


def get_jid(jid):
    """
    Merge the return data from all returners
    """
    ret = {}
    for returner_ in __opts__[CONFIG_KEY]:
        ret.update(_mminion().returners[f"{returner_}.get_jid"](jid))

    return ret


def get_jids():
    """
    Return all job data from all returners
    """
    ret = {}
    for returner_ in __opts__[CONFIG_KEY]:
        ret.update(_mminion().returners[f"{returner_}.get_jids"]())

    return ret


def clean_old_jobs():
    """
    Clean out the old jobs from all returners (if you have it)
    """
    for returner_ in __opts__[CONFIG_KEY]:
        fstr = f"{returner_}.clean_old_jobs"
        if fstr in _mminion().returners:
            _mminion().returners[fstr]()
