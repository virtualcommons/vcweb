{% for field in form %}
<div class='field'>
<span class='label'>{{ field.label_tag }}:</span>
{{ field }}
{% if field.errors %}
<label class='error' for='id_{{ field.name }}' generated='true'>{{ field.errors|join:". " }}</label>
{% endif %}
</div>
{% endfor %}
{% csrf_token %}
