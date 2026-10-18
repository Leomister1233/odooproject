from django.core.paginator import EmptyPage, Paginator


DEFAULT_PAGE_SIZE = 50
PAGE_SIZE_OPTIONS = (25, 50, 100)
TABLE_FETCH_LIMIT = 500


def get_page_window(request, prefix, default_page_size=DEFAULT_PAGE_SIZE):
    page_param = f"{prefix}_page"
    page_size_param = f"{prefix}_page_size"
    try:
        page_size = int(request.GET.get(page_size_param, default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = default_page_size
    try:
        page_number = max(1, int(request.GET.get(page_param, 1)))
    except (TypeError, ValueError):
        page_number = 1
    return {
        "page": page_number,
        "page_size": page_size,
        "offset": (page_number - 1) * page_size,
        "page_param": page_param,
        "page_size_param": page_size_param,
    }


def paginate_remote(request, items, total_count, prefix, default_page_size=DEFAULT_PAGE_SIZE):
    window = get_page_window(request, prefix, default_page_size)
    paginator = Paginator(range(max(0, int(total_count or 0))), window["page_size"])
    page_obj = paginator.get_page(window["page"])
    return {
        "items": list(items or []),
        "page_obj": page_obj,
        "page_param": window["page_param"],
        "page_size_param": window["page_size_param"],
        "page_size": window["page_size"],
        "page_size_options": PAGE_SIZE_OPTIONS,
        "total_count": paginator.count,
        "start_index": page_obj.start_index() if paginator.count else 0,
        "end_index": min(page_obj.start_index() + len(items or []) - 1, paginator.count) if items else 0,
    }


def paginate_items(request, items, prefix, default_page_size=DEFAULT_PAGE_SIZE):
    page_param = f"{prefix}_page"
    page_size_param = f"{prefix}_page_size"

    try:
        page_size = int(request.GET.get(page_size_param, default_page_size))
    except (TypeError, ValueError):
        page_size = default_page_size
    if page_size not in PAGE_SIZE_OPTIONS:
        page_size = default_page_size

    paginator = Paginator(items or [], page_size)
    try:
        page_number = int(request.GET.get(page_param, 1))
    except (TypeError, ValueError):
        page_number = 1

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    return {
        "items": list(page_obj.object_list),
        "page_obj": page_obj,
        "page_param": page_param,
        "page_size_param": page_size_param,
        "page_size": page_size,
        "page_size_options": PAGE_SIZE_OPTIONS,
        "total_count": paginator.count,
        "start_index": page_obj.start_index() if paginator.count else 0,
        "end_index": page_obj.end_index() if paginator.count else 0,
    }


def paginate_named_groups(request, groups, prefix):
    paginated_groups = {}
    for key, group in (groups or {}).items():
        pagination = paginate_items(request, group.get("rows", []), f"{prefix}_{key}")
        paginated_groups[key] = {
            **group,
            "rows": pagination["items"],
            "pagination": pagination,
        }
    return paginated_groups
