from .integrations import gcp


def get_url_for_ai_reply_obj(obj_name):
    return gcp.get_url_for_ai_reply_obj(obj_name)
