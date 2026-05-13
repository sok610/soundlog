from django import template

register = template.Library()

@register.filter
def get_item_prompt_id(answers_list, index):
    try:
        return answers_list[index].prompt.id
    except:
        return None

@register.filter
def get_item_text(answers_list, index):
    try:
        return answers_list[index].answer_text
    except:
        return ""