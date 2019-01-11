{# This is a copy of of the following file: #}
{# jupyter_contrib_nbextensions/templates/nbextensions.tpl#}
{# See https://github.com/ipython-contrib/jupyter_contrib_nbextensions/blob/master/COPYING.rst for licensing #}
{# It has been modified to support rst output#}
{%- extends 'rst.tpl' -%}

{% block input_group -%}
{%- if cell.metadata.hideCode or nb.metadata.hide_input -%}
{%- else -%}
    {{ super() }}
{%- endif -%}
{% endblock input_group %}

{% block output_group -%}
{%- if cell.metadata.hideOutput -%}
{%- else -%}
    {{ super() }}
{%- endif -%}
{% endblock output_group %}

{#{% block output_area_prompt %}#}
{#{%- if cell.metadata.hide_input or nb.metadata.hide_input -%}#}
{#    <div class="prompt"> </div>#}
{#{%- else -%}#}
{#    {{ super() }}#}
{#{%- endif -%}#}
{#{% endblock output_area_prompt %}#}
