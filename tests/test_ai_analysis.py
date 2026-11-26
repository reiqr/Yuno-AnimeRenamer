import io
import json
import unittest
from unittest.mock import Mock, patch

import ai_analysis


class AIAnalysisTests(unittest.TestCase):
    def test_request_sends_numbered_names_and_filters_invalid_suggestions(self):
        response = {'choices': [{'message': {'content':
            '```json\n{"1":"12.5","2":"../bad","3":"NCOP02","99":"7"}\n```'}}]}
        opener = Mock()
        opener.open.return_value = io.BytesIO(json.dumps(response).encode())
        settings = {'provider': 'DeepSeek', 'base_url': 'https://api.deepseek.com', 'model': 'test'}
        names = ['未来日记 12.5.mkv', 'Unknown.mkv', 'Show NCOP.mkv']
        with patch.object(ai_analysis, 'build_opener', return_value=opener):
            result = ai_analysis.analyze_filenames(settings, names, api_key='test-key')
        self.assertEqual(result, {0: '12.5', 2: 'NCOP02'})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.deepseek.com/chat/completions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-key')
        self.assertEqual(list(json.loads(json.loads(request.data)['messages'][1]['content']).values()), names)

    def test_changed_host_does_not_inherit_provider_key(self):
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'{"choices":[{"message":{"content":"{}"}}]}')
        settings = {'provider': 'OpenAI', 'base_url': 'https://custom.example/v1', 'model': 'test'}
        with patch.object(ai_analysis, 'build_opener', return_value=opener), \
                patch.dict(ai_analysis.os.environ, {'OPENAI_API_KEY': 'test-key'}):
            ai_analysis.analyze_filenames(settings, ['Show E01.mkv'])
        self.assertIsNone(opener.open.call_args.args[0].get_header('Authorization'))

    def test_only_loopback_can_use_http(self):
        with self.assertRaises(ValueError):
            ai_analysis.endpoint({'base_url': 'http://custom.example/v1', 'model': 'test'})
        self.assertEqual(ai_analysis.endpoint({'base_url': 'http://127.0.0.1:11434/v1',
                                               'model': 'test'}),
                         'http://127.0.0.1:11434/v1/chat/completions')
