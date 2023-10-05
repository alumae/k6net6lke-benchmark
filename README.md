# Eesti kõnetõlkeprojekti test-andmed ja skriptid
  
See repositoorium sisaldab TÜ/TTÜ kõnetõlkeprojekti testandmeid,
testimisskripti ning saadud tulemusi.

Kataloogis `data` on testandmed, lähtekeelte kaupa -- näiteks `data/et`
sisaldab eestikeelse sisendkõnega testandmeid. Failinimede kontseptsioon
on selline:

  * `<failinimi>.<sisendkeel>.OS.flac` -- sisendkõne 
  * `<failinimi>.<sihtkeel>.OSt` -- transkriptsioon antud keeles (võib olla tõlge)
  
  
NB! Selleks, et giti mitte suurte failidega koormata, helifaile siin repos pole.
Need tuleks (kui vaja) alla laadida ja lahti pakkida, selleks, siinsamas kataloogis käivitada:

    wget -O - https://cs.taltech.ee/staff/tanel.alumae/data/k6net6lge/k6net6lke-benchmark-audio.tar | tar xv 
    
Mingi süsteemi rakendamisena saadud tõlgitud andmed on üldjuhul mingis muus kataloogis (vaata näiteks 
`outputs/et/mt/whisper-large-v2/`. Siin on failinimede kontseptsioon: `<failinimi>.<sisendkeel>.<sihtkeel>.mt`

Selleks, et hinnata tõlkesüsteemi hüpoteeside BLEU skoori, käivita:

    ./run-mt-eval.sh --refdir <dir-with-reference-OSt-files> `
      --source <source_lang> --target <target_lang> <dir-with-output-files from-machine-translation>

NB! Enne peab olema installitud `SLTev` pythoni pakett (`pip3 install SLTev`).  
  
Tõlgitud andmed ei pea kasutama sama segmentatsiooni, mis referents-tõlked! Põhimõtteliselt võib 
tõlgitud tekst olla ka kõik ühel real. Joondus automaatsete tõlgete ja referents-tõlgete vahel leitakse automaatselt testimise käigus.
  

  
Näiteks:

    ./run-mt-eval.sh --refdir data/et --source et --target en outputs/et/mt/whisper-large-v2/
   
Tulemus:

    Evaluating the file  outputs/et/mt/whisper-large-v2//16.12.2020_-_Tallinna_Linnavalitsuse_kolmapäevane_pressikonverents-dGJ9HSmZR8A.et.en.mt  in terms of translation quality against  data/et/16.12.2020_-_Tallinna_Linnavalitsuse_kolmapäevane_pressikonverents-dGJ9HSmZR8A.en.OSt
    avg      sacreBLEU     mwerSegmenter          21.617
    Evaluating the file  outputs/et/mt/whisper-large-v2//Valitsuse_pressikonverents__15._oktoober_2020-dJypQ9rLypU.et.en.mt  in terms of translation quality against  data/et/Valitsuse_pressikonverents__15._oktoober_2020-dJypQ9rLypU.en.OSt
    avg      sacreBLEU     mwerSegmenter          13.083
    Evaluating the file  outputs/et/mt/whisper-large-v2//aktuaalne-kaamera-ilm-1001-317793.et.en.mt  in terms of translation quality against  data/et/aktuaalne-kaamera-ilm-1001-317793.en.OSt
    avg      sacreBLEU     mwerSegmenter          15.017
    Evaluating the file  outputs/et/mt/whisper-large-v2//aktuaalne-kaamera-ilm-1222-327710.et.en.mt  in terms of translation quality against  data/et/aktuaalne-kaamera-ilm-1222-327710.en.OSt
    avg      sacreBLEU     mwerSegmenter          20.158
    Evaluating the file  outputs/et/mt/whisper-large-v2//aktuaalne-kaamera-ilm-nadal-322248.et.en.mt  in terms of translation quality against  data/et/aktuaalne-kaamera-ilm-nadal-322248.en.OSt
    avg      sacreBLEU     mwerSegmenter          20.721
    Evaluating the file  outputs/et/mt/whisper-large-v2//ringvaade-2033-320571.et.en.mt  in terms of translation quality against  data/et/ringvaade-2033-320571.en.OSt
    avg      sacreBLEU     mwerSegmenter          17.167
    Evaluating the file  outputs/et/mt/whisper-large-v2//ringvaade-2071-326938.et.en.mt  in terms of translation quality against  data/et/ringvaade-2071-326938.en.OSt
    avg      sacreBLEU     mwerSegmenter          15.716


    Average BLEU:  17.6399
