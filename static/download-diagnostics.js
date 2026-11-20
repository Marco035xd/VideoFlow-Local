const downloadDiagnoses = {
  connection: ['Problema de conexión', 'Revisa tu conexión y vuelve a intentarlo. Si solo falla una plataforma, prueba ese enlace en el navegador.'],
  access: ['Acceso al video', 'Abre el enlace en el navegador y verifica si el sitio pide iniciar sesión o si el video sigue disponible.'],
  processing: ['Error de conversión', 'Comprueba que FFmpeg esté disponible en Configuración y prueba otro formato de salida.'],
  storage: ['Problema con el archivo o la carpeta', 'Comprueba que el archivo original exista y que puedas escribir en el destino. Revisa el espacio libre.'],
  format: ['Formato o pista no disponible', 'Vuelve a analizar el video y elige una calidad, un formato o una pista que siga disponible.'],
  unknown: ['Causa sin identificar', 'Si vuelve a fallar, puedes copiar este informe para pedir ayuda.'],
};

function openDownloadDiagnosis(task) {
  if (!task?.diagnostic) return;
  const t = window.VideoFlowI18n.t;
  const [category, advice] = downloadDiagnoses[task.diagnostic] || downloadDiagnoses.unknown;
  $('#diagnosisCategory').textContent = category;
  $('#diagnosisAdvice').textContent = advice;
  // Only include these known fields. Error details, video metadata and paths can contain private data.
  const source = ['YouTube', 'Facebook', 'TikTok', 'Reddit', 'Instagram', 'X', 'Twitch', 'Web', 'Local'].includes(task.source)
    ? task.source : '';
  const format = /^(mp4|mkv|webm|vob|mov|avi|mp3|m4a|wav|flac|ogg)$/i.test(task.format) ? task.format.toUpperCase() : '';
  $('#diagnosisReport').value = [
    'VideoFlow Local',
    t(category),
    source && `${t('Plataforma')} · ${t(source)}`,
    format && `${t('Formato')} · ${format}`,
    t(advice),
  ].filter(Boolean).join('\n');
  $('#downloadDiagnosis').showModal();
  $('#closeDiagnosis').focus();
}

$('#closeDiagnosis').addEventListener('click', () => $('#downloadDiagnosis').close());
$('#copyDiagnosis').addEventListener('click', async () => {
  const report = $('#diagnosisReport');
  try {
    await navigator.clipboard.writeText(report.value);
    $('#downloadDiagnosis').close();
    toast('Informe copiado', '', 'success');
  } catch {
    report.focus();
    report.select();
  }
});
