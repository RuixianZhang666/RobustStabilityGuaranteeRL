import tensorflow as tf
import os
from variant import *
from disturber.disturber import Disturber
import numpy as np
import time
import logger
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "1"



def get_distrubance_function(env_name):
    if 'cartpole_cost' in env_name:
        disturbance_step = cartpole_disturber
    elif 'HalfCheetah' in env_name:
        disturbance_step = halfcheetah_disturber
    else:
        disturbance_step = None
        print('no disturber designed for ' + env_name)
    return disturbance_step


def cartpole_disturber(time, s, action, env, eval_params, form_of_eval, disturber=None):
    if form_of_eval=='impulse':
        if time == eval_params['impulse_instant']:
            d = eval_params['magnitude'] * np.sign(s[0])
        else:
            d = 0
        s_, r, done, info = env.step(action, impulse=d)

    elif form_of_eval=='constant_impulse':
        if time % eval_params['impulse_instant']==0:
            d = eval_params['magnitude'] * np.sign(s[0])
        else:
            d = 0
        s_, r, done, info = env.step(action, impulse=d)
    elif form_of_eval == 'various_disturbance':
        if eval_params['form'] == 'sin':
            d = np.sin(2 *np.pi /eval_params['period'] * time + initial_pos) * eval_params['magnitude']
        s_, r, done, info = env.step(action, impulse=d)
    else:
        d, _ = disturber.choose_action(s, time)
        s_, r, done, info = env.step(action, process_noise=d)
    return s_, r, done, info


def halfcheetah_disturber(time, s, action, env, eval_params, form_of_eval, disturber=None):
    if form_of_eval == 'impulse':
        if time ==eval_params['impulse_instant']:
            # d = np.zeros([23])
            # d[3] = 1.

            # d = eval_params['magnitude'] * (-np.sign(action[3])) * d
            d = eval_params['magnitude'] * (-np.sign(action))
            d = np.concatenate([d, np.zeros([17])])
        else:
            d = np.zeros([23])
    elif form_of_eval == 'constant_impulse':
        if time % eval_params['impulse_instant'] == 0:
            d = eval_params['magnitude'] * (-np.sign(action))
            d = np.concatenate([d, np.zeros([17])])
        else:
            d = np.zeros([23])
    elif form_of_eval=='various_disturbance':
        if eval_params['form'] == 'sin':
            d = np.sin(2*np.pi/ eval_params['period'] * time + initial_pos) * eval_params['magnitude']

        d = np.concatenate([d, np.zeros([17])], axis=0)
    else:
        d, _ = disturber.choose_action(s, time)
        d = np.concatenate([d, np.zeros([17])], axis=0)
    s_, r, done, info = env.step(action, process_noise=d)
    return s_, r, done, info




def param_variation(variant):
    env_name = variant['env_name']
    env = get_env_from_name(env_name)
    env_params = variant['env_params']

    eval_params = variant['eval_params']
    policy_params = variant['alg_params']
    policy_params.update({
        's_bound': env.observation_space,
        'a_bound': env.action_space,
    })
    disturber_params = variant['disturber_params']
    build_func = get_policy(variant['algorithm_name'])
    s_dim = env.observation_space.shape[0]
    a_dim = env.action_space.shape[0]
    d_dim = env_params['disturbance dim']

    policy = build_func(a_dim, s_dim, d_dim, policy_params)
    # disturber = Disturber(d_dim, s_dim, disturber_params)

    param_variable = eval_params['param_variables']
    grid_eval_param = eval_params['grid_eval_param']
    length_of_pole, mass_of_pole, mass_of_cart, gravity = env.get_params()

    log_path = variant['log_path'] + '/eval'

    if eval_params['grid_eval']:

        param1 = grid_eval_param[0]
        param2 = grid_eval_param[1]
        log_path = log_path + '/' + param1 + '-'+ param2
        logger.configure(dir=log_path, format_strs=['csv'])
        logger.logkv('num_of_paths', variant['eval_params']['num_of_paths'])
        for var1 in param_variable[param1]:
            if param1 == 'length_of_pole':
                length_of_pole = var1
            elif param1 == 'mass_of_pole':
                mass_of_pole = var1
            elif param1 == 'mass_of_cart':
                mass_of_cart = var1
            elif param1 == 'gravity':
                gravity = var1

            for var2 in param_variable[param2]:
                if param2 == 'length_of_pole':
                    length_of_pole = var2
                elif param2 == 'mass_of_pole':
                    mass_of_pole = var2
                elif param2 == 'mass_of_cart':
                    mass_of_cart = var2
                elif param2 == 'gravity':
                    gravity = var2

                env.set_params(mass_of_pole=mass_of_pole, length=length_of_pole, mass_of_cart=mass_of_cart, gravity=gravity)
                diagnostic_dict = evaluation(variant, env, policy)

                string_to_print = [param1, ':', str(round(var1, 2)), '|', param2, ':', str(round(var2, 2)), '|']
                [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
                 for key in diagnostic_dict.keys()]
                print(''.join(string_to_print))

                logger.logkv(param1, var1)
                logger.logkv(param2, var2)
                [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
                logger.dumpkvs()
    else:
        for param in param_variable.keys():
            logger.configure(dir=log_path+'/'+param, format_strs=['csv'])
            logger.logkv('num_of_paths', variant['eval_params']['num_of_paths'])
            env.reset_params()
            for var in param_variable[param]:
                if param == 'length_of_pole':
                    length_of_pole = var
                elif param == 'mass_of_pole':
                    mass_of_pole = var
                elif param == 'mass_of_cart':
                    mass_of_cart = var
                elif param == 'gravity':
                    gravity = var

                env.set_params(mass_of_pole=mass_of_pole, length=length_of_pole, mass_of_cart=mass_of_cart, gravity=gravity)
                diagnostic_dict = evaluation(variant, env, policy)

                string_to_print = [param, ':', str(round(var, 2)), '|']
                [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
                 for key in diagnostic_dict.keys()]
                print(''.join(string_to_print))

                logger.logkv(param, var)
                [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
                logger.dumpkvs()


def instant_impulse(variant):
    env_name = variant['env_name']
    env = get_env_from_name(env_name)
    env_params = variant['env_params']

    eval_params = variant['eval_params']
    policy_params = variant['alg_params']
    disturber_params = variant['disturber_params']
    build_func = get_policy(variant['algorithm_name'])
    if 'Fetch' in env_name or 'Hand' in env_name:
        s_dim = env.observation_space.spaces['observation'].shape[0] \
                + env.observation_space.spaces['achieved_goal'].shape[0] + \
                env.observation_space.spaces['desired_goal'].shape[0]
    else:
        s_dim = env.observation_space.shape[0]
    a_dim = env.action_space.shape[0]
    d_dim = env_params['disturbance dim']
    policy = build_func(a_dim, s_dim, d_dim, policy_params)
    # disturber = Disturber(d_dim, s_dim, disturber_params)

    log_path = variant['log_path'] + '/eval/impulse'
    variant['eval_params'].update({'magnitude': 0})
    logger.configure(dir=log_path, format_strs=['csv'])
    for magnitude in eval_params['magnitude_range']:
        variant['eval_params']['magnitude'] = magnitude
        diagnostic_dict = evaluation(variant, env, policy)

        string_to_print = ['magnitude', ':', str(magnitude), '|']
        [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
         for key in diagnostic_dict.keys()]
        print(''.join(string_to_print))

        logger.logkv('magnitude', magnitude)
        [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
        logger.dumpkvs()

def constant_impulse(variant):
    env_name = variant['env_name']
    env = get_env_from_name(env_name)
    env_params = variant['env_params']

    eval_params = variant['eval_params']
    policy_params = variant['alg_params']
    disturber_params = variant['disturber_params']
    build_func = get_policy(variant['algorithm_name'])
    if 'Fetch' in env_name or 'Hand' in env_name:
        s_dim = env.observation_space.spaces['observation'].shape[0] \
                + env.observation_space.spaces['achieved_goal'].shape[0] + \
                env.observation_space.spaces['desired_goal'].shape[0]
    else:
        s_dim = env.observation_space.shape[0]
    a_dim = env.action_space.shape[0]
    d_dim = env_params['disturbance dim']
    policy = build_func(a_dim, s_dim, d_dim, policy_params)
    # disturber = Disturber(d_dim, s_dim, disturber_params)

    log_path = variant['log_path'] + '/eval/constant_impulse'
    variant['eval_params'].update({'magnitude': 0})
    logger.configure(dir=log_path, format_strs=['csv'])
    for magnitude in eval_params['magnitude_range']:
        variant['eval_params']['magnitude'] = magnitude
        diagnostic_dict = evaluation(variant, env, policy)

        string_to_print = ['magnitude', ':', str(magnitude), '|']
        [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
         for key in diagnostic_dict.keys()]
        print(''.join(string_to_print))

        logger.logkv('magnitude', magnitude)
        [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
        logger.dumpkvs()

def various_disturbance(variant):
    env_name = variant['env_name']
    env = get_env_from_name(env_name)
    env_params = variant['env_params']

    eval_params = variant['eval_params']
    policy_params = variant['alg_params']
    disturber_params = variant['disturber_params']
    build_func = get_policy(variant['algorithm_name'])
    if 'Fetch' in env_name or 'Hand' in env_name:
        s_dim = env.observation_space.spaces['observation'].shape[0] \
                + env.observation_space.spaces['achieved_goal'].shape[0] + \
                env.observation_space.spaces['desired_goal'].shape[0]
    else:
        s_dim = env.observation_space.shape[0]
    a_dim = env.action_space.shape[0]
    d_dim = env_params['disturbance dim']
    policy = build_func(a_dim, s_dim, d_dim, policy_params)
    # disturber = Disturber(d_dim, s_dim, disturber_params)

    log_path = variant['log_path'] + '/eval/various_disturbance-' + eval_params['form']
    variant['eval_params'].update({'period': 0})
    logger.configure(dir=log_path, format_strs=['csv'])
    for period in eval_params['period_list']:
        variant['eval_params']['period'] = period
        diagnostic_dict = evaluation(variant, env, policy)
        frequency = 1./period
        string_to_print = ['frequency', ':', str(frequency), '|']
        [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
         for key in diagnostic_dict.keys()]
        print(''.join(string_to_print))

        logger.logkv('frequency', frequency)
        [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
        logger.dumpkvs()

def trained_disturber(variant):
    env_name = variant['env_name']
    env = get_env_from_name(env_name)
    env_params = variant['env_params']

    eval_params = variant['eval_params']
    policy_params = variant['alg_params']
    disturber_params = variant['disturber_params']
    build_func = get_policy(variant['algorithm_name'])
    if 'Fetch' in env_name or 'Hand' in env_name:
        s_dim = env.observation_space.spaces['observation'].shape[0] \
                + env.observation_space.spaces['achieved_goal'].shape[0] + \
                env.observation_space.spaces['desired_goal'].shape[0]
    else:
        s_dim = env.observation_space.shape[0]
    a_dim = env.action_space.shape[0]
    d_dim = env_params['disturbance dim']
    policy = build_func(a_dim, s_dim, d_dim, policy_params)
    disturbance_chanel_list = np.nonzero(disturber_params['disturbance_magnitude'])[0]
    disturber_params['disturbance_chanel_list'] = disturbance_chanel_list
    disturber = Disturber(d_dim, s_dim, disturber_params)
    disturber.restore(eval_params['path'])

    log_path = variant['log_path'] + '/eval/trained_disturber'
    variant['eval_params'].update({'magnitude': 0})
    logger.configure(dir=log_path, format_strs=['csv'])

    diagnostic_dict = evaluation(variant, env, policy, disturber)

    string_to_print = []
    [string_to_print.extend([key, ':', str(round(diagnostic_dict[key], 2)), '|'])
     for key in diagnostic_dict.keys()]
    print(''.join(string_to_print))

    [logger.logkv(key, diagnostic_dict[key]) for key in diagnostic_dict.keys()]
    logger.dumpkvs()

def evaluation(variant, env, policy, disturber= None):
    env_name = variant['env_name']

    env_params = variant['env_params']
    disturbance_step = get_distrubance_function(env_name)
    max_ep_steps = env_params['max_ep_steps']

    eval_params = variant['eval_params']
    a_dim = env.action_space.shape[0]
    a_upperbound = env.action_space.high
    a_lowerbound = env.action_space.low
    # For analyse
    Render = env_params['eval_render']

    # Training setting

    total_cost = []
    death_rates = []
    form_of_eval = variant['evaluation_form']
    trial_list = os.listdir(variant['log_path'])
    episode_length = []


    for trial in trial_list:
        if trial == 'eval':
            continue
        if trial not in variant['trials_for_eval']:
            continue
        success_load = policy.restore(os.path.join(variant['log_path'], trial)+'/policy')
        if not success_load:
            continue
        die_count = 0
        seed_average_cost = []
        for i in range(int(np.ceil(eval_params['num_of_paths']/(len(trial_list)-1)))):

            cost = 0
            s = env.reset()
            if 'Fetch' in env_name or 'Hand' in env_name:
                s = np.concatenate([s[key] for key in s.keys()])
            global initial_pos
            initial_pos = np.random.uniform(0., np.pi, size=[a_dim])
            for j in range(max_ep_steps):
                if Render:
                    env.render()
                a = policy.choose_action(s, True)
                if variant['algorithm_name'] == 'LQR' or variant['algorithm_name'] == 'MPC':
                    action = a
                else:
                    action = a_lowerbound + (a + 1.) * (a_upperbound - a_lowerbound) / 2

                if form_of_eval == 'impulse' or form_of_eval == 'constant_impulse' \
                        or form_of_eval == 'various_disturbance':

                    s_, r, done, info = disturbance_step(j, s, action, env, eval_params, form_of_eval)
                elif form_of_eval == 'trained_disturber':
                    s_, r, done, info = disturbance_step(j, s, action, env, eval_params, form_of_eval, disturber=disturber)
                else:
                    s_, r, done, info = env.step(action)

                cost += r
                if 'Fetch' in env_name or 'Hand' in env_name:
                    s_ = np.concatenate([s_[key] for key in s_.keys()])
                    if info['done'] > 0:
                        done = True

                if j == max_ep_steps - 1:
                    done = True
                s = s_
                if done:
                    if variant['algorithm_name'] == 'LQR':
                        policy.reset()
                    seed_average_cost.append(cost)
                    episode_length.append(j)
                    if j < max_ep_steps-1:
                        die_count += 1
                    break
        death_rates.append(die_count/(i+1)*100)
        total_cost.append(np.mean(seed_average_cost))

    total_cost_std = np.std(total_cost, axis=0)
    total_cost_mean = np.average(total_cost)
    death_rate = np.mean(death_rates)
    death_rate_std = np.std(death_rates, axis=0)
    average_length = np.average(episode_length)

    diagnostic = {'return': total_cost_mean,
                  'return_std': total_cost_std,
                  'death_rate': death_rate,
                  'death_rate_std': death_rate_std,
                  'average_length': average_length}
    return diagnostic

def training_evaluation(variant, env, policy, disturber= None):
    env_name = variant['env_name']

    env_params = variant['env_params']

    max_ep_steps = env_params['max_ep_steps']

    eval_params = variant['eval_params']

    a_upperbound = env.action_space.high
    a_lowerbound = env.action_space.low
    # For analyse
    Render = env_params['eval_render']

    # Training setting

    total_cost = []
    death_rates = []
    form_of_eval = variant['evaluation_form']
    trial_list = os.listdir(variant['log_path'])
    episode_length = []




    die_count = 0
    seed_average_cost = []
    for i in range(variant['store_last_n_paths']):

        cost = 0
        s = env.reset()

        for j in range(max_ep_steps):
            if Render:
                env.render()
            a = policy.choose_action(s, True)
            if variant['algorithm_name'] == 'LQR':
                action = a
            else:
                action = a_lowerbound + (a + 1.) * (a_upperbound - a_lowerbound) / 2

            s_, r, done, info = env.step(action)

            cost += r
            if 'Fetch' in env_name or 'Hand' in env_name:
                s_ = np.concatenate([s_[key] for key in s_.keys()])
                if info['done'] > 0:
                    done = True

            if j == max_ep_steps - 1:
                done = True
            s = s_
            if done:
                seed_average_cost.append(cost)
                episode_length.append(j)
                if j < max_ep_steps-1:
                    die_count += 1
                break
    death_rates.append(die_count/(i+1)*100)
    total_cost.append(np.mean(seed_average_cost))

    total_cost_std = np.std(total_cost, axis=0)
    total_cost_mean = np.average(total_cost)
    death_rate = np.mean(death_rates)
    death_rate_std = np.std(death_rates, axis=0)
    average_length = np.average(episode_length)

    diagnostic = {'return': total_cost_mean,
                  'average_length': average_length}
    return diagnostic



if __name__ == '__main__':
    for name in VARIANT['eval_list']:
        VARIANT['log_path'] = '/'.join(['./log', VARIANT['env_name'], name])

        if 'LAC' in name:
            VARIANT['alg_params'] = ALG_PARAMS['RLAC']
            VARIANT['algorithm_name'] = 'RLAC'
        elif'RARL' in name:
            VARIANT['alg_params'] = ALG_PARAMS['RARL']
            VARIANT['algorithm_name'] = 'RARL'
        elif 'SAC' in name:
            VARIANT['alg_params'] = ALG_PARAMS['SAC_cost']
            VARIANT['algorithm_name'] = 'SAC_cost'
        else:
            VARIANT['alg_params'] = ALG_PARAMS['LQR']
            VARIANT['algorithm_name'] = 'LQR'
        print('evaluating '+name)
        if VARIANT['evaluation_form'] == 'param_variation':
            param_variation(VARIANT)
        elif VARIANT['evaluation_form'] == 'trained_disturber':
            trained_disturber(VARIANT)
        elif VARIANT['evaluation_form'] == 'various_disturbance':
            various_disturbance(VARIANT)
        elif VARIANT['evaluation_form'] == 'constant_impulse':
            constant_impulse(VARIANT)
        else:
            instant_impulse(VARIANT)
        tf.reset_default_graph()

