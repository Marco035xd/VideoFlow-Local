import os, tempfile, pathlib, sys, subprocess, time, hashlib, json
root=pathlib.Path.cwd(); sys.path.insert(0,str(root))
with tempfile.TemporaryDirectory(prefix='videoflow-check-') as directory:
 os.environ['VIDEOFLOW_DATA_DIR']=str(pathlib.Path(directory)/'data')
 import app
 client=app.app.test_client(); ff=app.find_tool('ffmpeg'); fp=app.find_tool('ffprobe')
 source=pathlib.Path(directory)/'sample.mp4'
 subprocess.run([ff,'-v','error','-f','lavfi','-i','color=c=blue:s=160x120:d=2','-f','lavfi','-i','sine=frequency=440:duration=2','-c:v','libx264','-c:a','aac','-shortest',str(source)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 jobs=[]
 for fmt in ['mp3','m4a','wav','flac']:
  response=client.post('/api/convert',json={'path':str(source),'format':fmt,'quality':'192','folder':str(pathlib.Path(directory)/'audio')})
  assert response.status_code==201,response.json
  jobs.append(response.json['download']['id'])
 deadline=time.time()+45
 while time.time()<deadline and any(app.download_manager.get(j).status not in {'Completado','Error','Cancelado'} for j in jobs):time.sleep(.2)
 for j in jobs:
  task=app.download_manager.get(j);assert task.status=='Completado',(task.status,task.error)
  result=subprocess.run([fp,'-v','error','-show_streams','-of','json',task.final_path],capture_output=True,text=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  assert [s['codec_type'] for s in json.loads(result.stdout)['streams']]==['audio']
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 assert len(client.get('/api/history').json['history'])==4
 assert client.post('/api/convert',json={'path':str(source),'format':'exe'}).status_code==400
 assert client.put('/api/settings',json={'rate_limit_kbps':512,'retry_count':8}).status_code==200
 assert client.get('/api/settings').json['settings']['retry_count']==8
 assert client.put('/api/settings',json={'retry_count':-1}).status_code==400
 silent=pathlib.Path(directory)/'silent.mp4'
 subprocess.run([ff,'-v','error','-f','lavfi','-i','color=s=160x120:d=1','-an',str(silent)],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
 response=client.post('/api/convert',json={'path':str(silent),'format':'mp3','folder':str(pathlib.Path(directory)/'audio')})
 task=app.download_manager.get(response.json['download']['id'])
 deadline=time.time()+10
 while time.time()<deadline and task.status not in {'Error','Completado'}:time.sleep(.1)
 assert task.status=='Error' and 'pista de audio' in task.error
 print('OK: cuatro formatos de audio, fuente intacta, historial, validación de ajustes y video sin audio.')

import local_audio
child = local_audio.start_process([sys.executable, '-c', 'import time; time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
local_audio.shutdown()
assert child.poll() is not None
print('OK: cierre de procesos de conversión al salir.')
