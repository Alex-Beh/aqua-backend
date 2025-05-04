# app/utils/pagination.py

import math


def paginate_response(query, page, size, model_class, sort_field=None, sort_order='asc'):
    """
    Paginates the query result and supports sorting.
    :param query: SQLAlchemy query object
    :param page: Page number
    :param size: Number of items per page
    :param model_class: Model class for the query results, used for counting total items
    :param sort_field: Field name to sort by (optional)
    :param sort_order: 'asc' for ascending or 'desc' for descending (default is 'asc')
    :return: A dictionary with paginated and sorted data
    """
    # Sorting logic
    # Only apply sort if not already applied (assuming external logic handles it)
    if sort_field and not query._order_by_clauses:
        sort_func = getattr(model_class, sort_field, None)
        if sort_func:
            if sort_order == 'desc':
                query = query.order_by(sort_func.desc())
            else:
                query = query.order_by(sort_func)

    total = query.count()
    total_pages = math.ceil(total / size) if size > 0 else 0
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        'total': total,
        'totalPages': total_pages,
        'page': page,
        'size': size,
        'items': [item.to_dict() for item in items]  # Assuming `to_dict()` method is available on model class
    }
