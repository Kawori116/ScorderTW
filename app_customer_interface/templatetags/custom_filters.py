from django import template

register = template.Library()

@register.filter
def item_total_price(item):
    return item.dish.price * item.quantity


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0.0

@register.filter
def split_lines(value):
    return value.split('\n')

@register.filter(name='make_range')
def make_range(number):
    return range(number+1)

# @register.filter(name='range')
# def filter_range(start, end):
#     return range(start, end)