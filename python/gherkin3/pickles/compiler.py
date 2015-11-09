import io
import os
import json
import re

from ..dialect import Dialect

def compile(feature, path):
    pickles          = []
    dialect          = feature['language']
    feature_tags     = feature['tags']
    background_steps = _get_background_steps(feature)
    for scenario_definition in feature['scenarioDefinitions']:
        args = feature_tags, background_steps, scenario_definition, dialect, path, pickles
        if scenario_definition['type'] is 'Scenario':
            _compile_scenario(*args)
        else:
            _compile_scenario_outline(*args)
    return pickles

def _compile_scenario(feature_tags, background_steps, scenario, dialect, path, pickles):
    steps = list(background_steps)
    tags  = list(feature_tags) + list(scenario['tags'])
    
    for step in scenario['steps']:
        steps.append(_pickle_step(step))

    pickle = {
        'path':     path,
        'tags':     _pickle_tags(tags),
        'name':     '{0[keyword]}: {0[name]}'.format(scenario),
        'locations':[_pickle_location(scenario['location'])],
        'steps':    steps
    }
    pickles.append(pickle)

def _compile_scenario_outline(feature_tags, background_steps, scenario_outline, dialect, path, pickles):
    keyword = Dialect.for_name(dialect).scenario_keywords[0]
    
    for examples in scenario_outline['examples']:
        variable_cells = examples['tableHeader']['cells']
        
        for values in examples['tableBody']:
            value_cells = values['cells']
            steps       = list(background_steps)
            tags        = list(feature_tags) + list(scenario_outline['tags']) + list(examples['tags'])
            
            for scenario_outline_step in scenario_outline['steps']:
                step_text = _interpolate(scenario_outline_step['text'], variable_cells, value_cells)
                arguments = _create_pickle_arguments(scenario_outline_step.get('argument'), variable_cells, value_cells)
                _pickle_step = {
                    'text': step_text,
                    'arguments': arguments,
                    'locations': [
                        _pickle_location(values['location']),
                        _pickle_step_location(scenario_outline_step)
                    ]
                }
                steps.append(_pickle_step)

            pickle = {
                'path':  path,
                'name':  '{0}: {1}'.format(keyword, _interpolate(scenario_outline['name'], variable_cells, value_cells)),
                'steps': steps,
                'tags':  _pickle_tags(tags),
                'locations': [
                    _pickle_location(values['location']),
                    _pickle_location(scenario_outline['location'])
                ]
            }
            pickles.append(pickle)

def _create_pickle_arguments(argument, variables, values):
    result = []
    
    if not argument:
        return result
    
    if argument['type'] is 'DataTable':
        table = { 'rows': [] }
        for row in argument['rows']:
            cells = [
                {   
                    'location': _pickle_location(cell['location']),
                    'value':    _interpolate(cell['value'], variables, values) 
                } for cell in row['cells']
            ]
            table['rows'].append(cells)
        result.append(table)
    
    elif argument['type'] is 'DocString':
        docstring = {
            'location': _pickle_location(argument['location']),
            'content':  _interpolate(argument['content'], variables, values)
        }
        result.append(docstring)
    
    else:
        raise Exception('Internal error')
    
    return result

def _interpolate(name, variable_cells, value_cells):
    for n, variable_cell in enumerate(variable_cells):
        value_cell  = value_cells[n]
        name        = re.sub( 
            '<{0[value]}>'.format(variable_cell),
            value_cell['value'],
            name
            )
    return name

def _get_background_steps(feature):
    if 'background' in feature:
        return [_pickle_step(step) for step in feature['background']['steps']]
    return []

def _pickle_step(step):
    return {
        'text':      step['text'],
        'arguments': _create_pickle_arguments(step.get('argument'), [], []),
        'locations': [_pickle_step_location(step)]
    }

def _pickle_step_location(step):
    return {
        'line':   step['location']['line'],
        'column': step['location']['column'] + len( step.get('keyword', 0) )
    }

def _pickle_location(location):
    return {
        'line':   location['line'],
        'column': location['column']
    }

def _pickle_tags(tags):
    return [_pickle_tag(tag) for tag in tags]

def _pickle_tag(tag):
    return {
        'name':     tag['name'],
        'location': _pickle_location(tag['location'])
    }