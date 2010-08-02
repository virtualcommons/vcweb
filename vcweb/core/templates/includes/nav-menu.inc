{% load tags %}

{% url home as home %}
{% url about as about %}
{% url core:login as login %}
{% url core:logout as logout %}
{% url core:register as register %}

<div id='menu'>
<ul>
	<li class='{% active request "^/$" %}'' ><a href='/' class='first'>Home</a></li>
	<li class='{% active request about %}'><a href='{{ about }}'>About</a></li>
	<li><a class='external' href='http://commons.asu.edu/contact/'>Contact us</a></li>
	{% if request.is_authenticated %}
	<li class='{% active request logout %}'><a href='{{ logout }}'>Logout</a></li>
	{% else %}
	<li class='{% active request login %} {% active request register %}'><a href='{{ login }}'>Login/Register</a></li>
	{% endif %}
</ul>
</div>