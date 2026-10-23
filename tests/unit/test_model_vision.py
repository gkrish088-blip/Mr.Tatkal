import json
import httpx
import pytest
from harness.models.adapter import HTTPModel, ModelConfig


@pytest.mark.parametrize('protocol', ['chat', 'messages'])
async def test_latest_two_images_sent_in_provider_format(tmp_path,monkeypatch,protocol):
    monkeypatch.setenv('MODEL_TEST_KEY','test-only')
    paths=[]
    for index in range(3):
        path=tmp_path/f'{index}.png';path.write_bytes(b'fixture-bytes');paths.append(str(path))
    context={'observation':{'screenshot':paths[2]},'history':[{'after':{'screenshot':p}} for p in paths]}
    def transport(request):
        payload=json.loads(request.content)
        blocks=payload['messages'][-1]['content']
        assert len(blocks)==3
        image=blocks[1]
        assert image['type']==('image' if protocol=='messages' else 'image_url')
        if protocol=='messages':
            assert image['source']['media_type']=='image/png'
            response={'content':[{'type':'text','text':'DONE'}]}
        else:
            assert image['image_url']['url'].startswith('data:image/png;base64,')
            response={'choices':[{'message':{'content':'DONE'}}]}
        return httpx.Response(200,json=response)
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result=await HTTPModel(ModelConfig('https://fixture.test/v1','fixture','MODEL_TEST_KEY',protocol),client).decide(context,[])
    assert result.done
