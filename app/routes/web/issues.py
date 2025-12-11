from . import bp as web_bp

@web_bp.get("/issues", strict_slashes=False, endpoint="issues_list")
def issues_list():
    # TODO: implement real listing later
    return "Issues list placeholder"