# -*- coding: utf-8 -*-


from django.db import migrations


def add_round(cfg,
              round_type=None, sequence_number=None, template_id=None, repeat=0, duration=45, session_id='',
              preserve_existing_groups=True, randomize_groups=False, chat_enabled=False, survey_url='',
              initialize_data_values=False,
              **kwargs):
    if sequence_number is None:
        sequence_number = cfg.round_configuration_set.count() + 1
    if template_id is None:
        template_id = round_type
    return cfg.round_configuration_set.create(
        round_type=round_type,
        sequence_number=sequence_number,
        template_id=template_id,
        repeat=repeat,
        duration=duration,
        session_id=session_id,
        preserve_existing_groups=preserve_existing_groups,
        randomize_groups=randomize_groups,
        chat_enabled=chat_enabled,
        survey_url=survey_url,
        initialize_data_values=initialize_data_values,
        **kwargs
    )


def create_forestry_configuration(apps, schema_editor):
    ExperimentMetadata = apps.get_model('core', 'ExperimentMetadata')
    ExperimentConfiguration = apps.get_model('core', 'ExperimentConfiguration')
    Experimenter = apps.get_model('core', 'Experimenter')
    Parameter = apps.get_model('core', 'Parameter')
    forestry_experiment_metadata = ExperimentMetadata.objects.get(namespace='forestry')
    cfg = ExperimentConfiguration.objects.create(
        experiment_metadata=forestry_experiment_metadata,
        creator=Experimenter.objects.first(),
        name='Communication and Motives for Self-Governance Experiment',
        description='Communication and Motives for Self-Governance Forestry Experiment by DeCaro and Lee',
        max_group_size=4,
        exchange_rate=0.05,
        show_up_payment=0.00,
        maximum_payment=25.00,
        treatment_id='daniel.decaro/t1'
    )
    initial_resource_level_parameter = Parameter.objects.get(name='initial_resource_level')
    reset_resource_level_parameter = Parameter.objects.get(name='reset_resource_level')
    regrowth_rate_parameter = Parameter.objects.get(name='regrowth_rate')

    def reset_resource_level(r):
        r.parameter_value_set.create(parameter=reset_resource_level_parameter,
                                     boolean_value=True)
        r.parameter_value_set.create(parameter=initial_resource_level_parameter,
                                     int_value=100)
        r.parameter_value_set.create(parameter=regrowth_rate_parameter,
                                     float_value=0.2)

    add_round(cfg, round_type='WELCOME', sequence_number=1, duration=0)
    general_instructions = add_round(cfg, round_type='GENERAL_INSTRUCTIONS', sequence_number=2, duration=0)
    general_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    practice_round = add_round(cfg, round_type='PRIVATE_PRACTICE', template_id='PRACTICE', sequence_number=3, repeat=3,
                               initialize_data_values=True, randomize_groups=True, preserve_existing_groups=False,
                               duration=0)
    reset_resource_level(practice_round)
# Phase one, NC
    add_round(cfg, round_type='DEBRIEFING', sequence_number=4, template_id='PRACTICE_ROUND_RESULTS', duration=0)
    phase_one_part_one = add_round(cfg, round_type='REGULAR', sequence_number=5, repeat=6, initialize_data_values=True,
                                   duration=45, randomize_groups=True, preserve_existing_groups=False)
# reset resource level
    reset_resource_level(phase_one_part_one)

    phase_one_part_two_instructions = add_round(cfg, round_type='INSTRUCTIONS', sequence_number=6, template_id='PHASE_ONE_BLOCK_ONE_RESULTS', duration=0)
    phase_one_part_two_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    phase_one_part_two = add_round(cfg, round_type='REGULAR', sequence_number=7, repeat=6, initialize_data_values=True,
                                   duration=45)
    reset_resource_level(phase_one_part_two)
# reset resource level again
    # Survey 1 and Phase 2, C
    phase_two_instructions = add_round(cfg, round_type='INSTRUCTIONS', sequence_number=8,
                                       survey_url='https://louisville.az1.qualtrics.com/SE/?SID=SV_0BSEhpRIzeZi501',
                                       template_id='PHASE_TWO_INSTRUCTIONS', duration=0)
    phase_two_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    # dedicated 5 minute communication round
    add_round(cfg, round_type='CHAT', sequence_number=9, template_id='COMMUNICATION', chat_enabled=True, duration=300)
    phase_two_part_one = add_round(cfg, round_type='REGULAR', sequence_number=10, repeat=6, chat_enabled=True,
                                   initialize_data_values=True, duration=45)
    reset_resource_level(phase_two_part_one)

    phase_two_block_two_instructions = add_round(cfg, round_type='INSTRUCTIONS', sequence_number=11, template_id='PHASE_TWO_BLOCK_ONE_RESULTS', duration=0)
    phase_two_block_two_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    add_round(cfg, round_type='CHAT', sequence_number=12, template_id='COMMUNICATION', chat_enabled=True, duration=300)
    phase_two_part_two = add_round(cfg, round_type='REGULAR', sequence_number=13, repeat=6, chat_enabled=True,
                                   initialize_data_values=True, duration=45)
    reset_resource_level(phase_two_part_two)

    # Survey 2 and Phase 3, NC/C
    phase_three_instructions = add_round(cfg, round_type='INSTRUCTIONS', sequence_number=14,
                                         survey_url='https://louisville.az1.qualtrics.com/SE/?SID=SV_eWi6whndxg1wQjr',
                                         template_id='PHASE_THREE_INSTRUCTIONS', duration=0)
    phase_three_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    phase_three_part_one = add_round(cfg, round_type='REGULAR', sequence_number=15, repeat=6,
                                     initialize_data_values=True, duration=45)
    reset_resource_level(phase_three_part_one)

    phase_three_block_two_instructions = add_round(cfg, round_type='INSTRUCTIONS', sequence_number=16, template_id='PHASE_THREE_BLOCK_ONE_RESULTS',
                                                   duration=0)
    phase_three_block_two_instructions.parameter_value_set.create(parameter=initial_resource_level_parameter, int_value=100)
    phase_three_part_two = add_round(cfg, round_type='REGULAR', sequence_number=17, repeat=6,
                                     initialize_data_values=True, duration=45)
    reset_resource_level(phase_three_part_two)

    # Survey three and final debriefing
    add_round(cfg, round_type='DEBRIEFING', sequence_number=18, survey_url='https://louisville.az1.qualtrics.com/SE/?SID=SV_5dQLvcx7XMiQnpH',
              template_id='FINAL_DEBRIEFING', duration=0)


def rollback_forestry_configuration(apps, schema_editor):
    ExperimentConfiguration = apps.get_model('core', 'ExperimentConfiguration')
    ExperimentConfiguration.objects.get(treatment_id='daniel.decaro/t1').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('forestry', '0001_initial_forestry'),
    ]

    operations = [
        migrations.RunPython(create_forestry_configuration, rollback_forestry_configuration)
    ]
