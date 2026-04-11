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

## ASR hindamine (`run-asr-eval.sh`)

ASR väljundite hindamiseks käivita:

    ./run-asr-eval.sh --refdir <dir-with-reference-OSt-files> --source <source_lang> <dir-with-asr-output-files>

Näiteks:

    ./run-asr-eval.sh outputs/et/asr/whisper-large-v3-et-orthographic

Vaikimisi rakendab skript **õiglast normaliseerimispipeliini**, mis hoiab
ära selle, et `Covid-19` vs `Covid üheksateist`, suitsujutumärgid,
Unicode-mõttekriipsud, suuruskestel eraldatud sidekriipsud jms muutuksid
tehislikeks WER-vigadeks. Pipeline rakendatakse nii referentsile kui
ka hüpoteesile enne skoorimist:

1. Unicode NFC.
2. `estnltk` compound-token tagger leiab kuupäevad, kellaajad, numbrid,
   sidekriipsuga ühendid, emaili/URL-i tokenid jne; iga tüüp saab oma
   ümberkirjutuse (numbrid sõnadeks läbi sisseehitatud eesti arvude
   kirjutaja, emailid/URL-id kustutatakse).
3. Ühikute/sümbolite tabel (`%` → `protsenti`, `°C` → `kraadi`, ...).
4. Kõik ülejäänud arvud sõnadeks.
5. Kirjavahemärgid (nii ASCII kui ka Unicode `P*` kategooria) → tühik,
   **mitte kustutus** — see on otse parandus `SLTev/ASRev.py`-s olevale
   veale, kus `Covid-19` muudeti tokeniks `covid19`.
6. Lowercase.
7. Tühikud kokku.

WER-skoor esitatakse nii makro- (failide keskmine) kui ka mikro- (kogu
editide summa / referentsi sõnade koguarv) keskmisena. **Vaatle eelkõige
mikro-WER-i** — see on tööstuse standard ja raporteeritud
number publikatsioonides.

Vaata `BENCHMARK_ISSUES.md` üksikasjalikku selgitust miks eelmine
`ASReval --simple` pipeline ei olnud õiglane.

Vanu `RESULTS.md` numbreid saab reprodutseerida `--normalize false`
lipuga:

    ./run-asr-eval.sh --normalize false outputs/et/asr/whisper-large-v3-et-orthographic

Uued sõltuvused (lisaks `SLTev`-le):

    pip3 install jiwer estnltk num2words
    # valikuliselt, parema inglise normaliseerimise jaoks:
    pip3 install -U openai-whisper


Selleks, et hinnata tõlkesüsteemi hüpoteeside BLEU skoori, käivita:

    ./run-mt-eval.sh --refdir <dir-with-reference-OSt-files> \
      --source <source_lang> --target <target_lang> <dir-with-output-files-from-machine-translation>

NB! Enne peab olema installitud `SLTev` pythoni pakett (`pip3 install SLTev`) —
vajalik ainult siis, kui soovid käivitada vana (backwards-compat) pipeline'i
`--normalize false` lipuga. Uue (õiglase) pipeline'i jaoks vaja `jiwer`,
`sacrebleu`, `estnltk` ja `num2words` (vt allpool).

Tõlgitud andmed ei pea kasutama sama segmentatsiooni, mis referents-tõlked! Põhimõtteliselt võib 
tõlgitud tekst olla ka kõik ühel real. Joondus automaatsete tõlgete ja referents-tõlgete vahel leitakse automaatselt testimise käigus.

**Vaikimisi** rakendab `run-mt-eval.sh` sama õiglast normaliseerimispipeliini
kui `run-asr-eval.sh` (vt allpool ja `BENCHMARK_ISSUES.md`): nii referents
kui ka MT väljund läbivad keelespetsiifilise normaliseerija (eesti keel:
sisseehitatud arvude kirjutaja; vene keel: `num2words(lang='ru')`; inglise
keel: Whisper `EnglishTextNormalizer`), misjärel arvutatakse
**korpustasemel sacreBLEU** (`13a` tokeniser, vastavalt sacreBLEU-st
leitav tavaline konventsioon), mitte makro-keskmist per-file BLEU-d.
See kõrvaldab BLEU-nihke, mis tekib siis, kui MT süsteemi väljund kirjutab
numbreid digitaalselt (nt "55") samal ajal kui referents-tõlge on sõnades
("viiskümmend viis" / "fifty-five" / "пятьдесят пять").

Vanade `RESULTS.md` numbrite reprodutseerimiseks kasuta `--normalize false`:

    ./run-mt-eval.sh --normalize false --target en outputs/et/mt/whisper-large-v2

Vt `BENCHMARK_ISSUES.md` täielikku ülevaadet sellest, miks vana `ASReval`-
ja `MTeval`-põhine pipeline ei olnud õiglane süsteemide võrdlemiseks.
  

  
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
