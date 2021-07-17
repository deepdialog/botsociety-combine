import re
import json
import yaml


def extract(example):
    """把nlu中的内容处理一下，返回其中的原文本和实体
    例如输入文本是：“[北京](city)的天气”
    输出的是："北京的天气"，[(北京,city)]
    """
    entities = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', example)
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', '\\1', example)
    return text, entities


def convert(nlu_path, json_path):
    """导出数据
    nlu_path: nlu.yaml的路径
    json_path: 导出的json的路径
    """
    with open(nlu_path) as fp:
        yaml_data = yaml.load(fp, Loader=yaml.BaseLoader)

    with open(json_path) as fp:
        json_data = json.load(fp)

    all_text_entities = {}
    for intent_examples in yaml_data['nlu']:
        intent = intent_examples['intent']
        examples = intent_examples['examples']
        if isinstance(examples, str):
            examples = yaml.load(examples, Loader=yaml.BaseLoader)
        text_entities = {
            x[0]: x[1]
            for x in
            [extract(x) for x in examples]
        }
        for k, v in text_entities.items():
            all_text_entities[intent + ':' + k] = v

    all_text_entities

    id_is_bot = {x['_id']: x['bot'] or 'Bot' in x['name'] for x in json_data['persons']}
    id_msg = {x['id']: x for x in json_data['messages']}
    id_intent_name = {x['_id']: x['name'] for x in json_data['intents']}

    new_stories = "version: '2.0'\nstories:"
    for story in json_data['paths']:
        new_story = '\n  - story: ' + story.get('name')
        new_story += '\n    steps:\n'
        steps = []
        for msg_id in story['messageIds']:
            msg = id_msg[msg_id]
            obj = {
                'intent': id_intent_name[msg['intentId']]
            } if not id_is_bot[msg['senderId']] else {
                'action': id_intent_name[msg['intentId']]
            }
            if 'intent' in obj:
                text = msg['attachments'][0]['utterances'][0]['components'][0]['text']
                key = obj['intent'] + ':' + text
                entities = all_text_entities.get(key, [])
                steps.append('- intent: ' + obj['intent'])
                if len(entities) > 0:
                    steps.append('  entities:')
                    for a, b in entities:
                        steps.append('  - ' + b + ': ' + a)
            else:
                steps.append('- action: ' + 'utter_' + obj['action'])
        new_story += '\n'.join([('      ' + x) for x in steps])
        new_stories += new_story

    return new_stories

def main(nlu_path, json_path, output=None):
    """Generate stories with nlu.yaml and xxxxx.json, which you exported from botsociety.

    python botsociety-convert.py path_to_nlu.yaml path_to_json.json

    Args:
        nlu_path: the path to nlu.yaml, you should unpack the ***-rasa.zip
        json_path: json from botsociety, like a7e6a2c9-ae9d-d208-9e47-adc80eeed1df-export.json
        output: Optional, default print to console, or a file_path to save the export
    """
    result_yaml = convert(nlu_path, json_path)
    good = True
    try:
        test = yaml.load(result_yaml, Loader=yaml.BaseLoader)
    except:
        good = False
    if not good:
        print('YAML invalid')
    else:
        if isinstance(output, str):
            with open(output, 'w') as fp:
                fp.write(result_yaml)
        else:
            print(result_yaml)

if __name__ == '__main__':
    import fire
    fire.Fire(main)
