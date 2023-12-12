Generated using:

    for f in outputs/et/asr/whisper-medium-et-orthographic/*.et.asr; do python utils/neurotolge-translate.py  et ru $f outputs/et/mt/whisper-medium-et-orthographic-neurotolge/`basename $f .et.asr`.et.ru.mt; done
