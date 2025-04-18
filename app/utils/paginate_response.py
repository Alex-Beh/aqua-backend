# app/utils/pagination.py

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
    if sort_field:
        sort_func = getattr(model_class, sort_field, None)
        if sort_func:
            if sort_order == 'desc':
                query = query.order_by(sort_func.desc())
            else:
                query = query.order_by(sort_func)

    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()

    return {
        'total': total,
        'page': page,
        'size': size,
        'items': [item.to_dict() for item in items]  # Assuming `to_dict()` method is available on model class
    }
