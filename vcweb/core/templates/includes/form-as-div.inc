{% for field in form %}
<div class='field'>
<span class='input-errors'>{{ field.errors }}</span>
<span class='label'>{{ field.label_tag }}:</span>
<span class='input-field'> {{ field }} </span>
</div>
{% endfor %}

