function mt_start_systeem(){
    console.log("go");
//    document.getElementById("beantwoordknop").innerHTML = 'waiting for answer';
//    document.getElementById("beantwoordknop").disabled = true;
    const kandidaatnr = document.getElementById("kandidaatnr").value;
    const opleidingsnr = document.getElementById("opleidingsnr").value;
    let verzendObject = JSON.stringify({kandidaatnr, opleidingsnr, kennismatrix});
    post_fetch("/mt_start_systeem",verzendObject, mt_verwerk_response);
}
function mt_verwerk_response(data){
                
            let titeljouwantwoord = document.getElementById("titeljouwantwoord");
            titeljouwantwoord.innerHTML = 'Jouw Antwoord:';
            titeljouwantwoord.style.color = '#22345b';

            console.log("hier", data);
            document.getElementById("vraag").innerHTML = data.volgendevraag;
            if(data.volgendevraag == ""){
                alert("het onderzoek is afgerond, u hoeft geen vragen meer te beantwoorden");
                document.getElementById("antwoord").innerHTML = 'u hoeft geen vragen meer te beantwoorden <button onclick=maakrapportage()>Toon Verslag</button>';
                document.getElementById("antwoord").disabled = true;
        //        document.getElementById("beantwoordknop").disabled = true;

            }else{
                document.getElementById("antwoord").innerHTML = toonAntwoordKnoppen(data);
                document.getElementById("antwoord").disabled = false;
//                document.getElementById("beantwoordknop").disabled = false;
//                document.getElementById("beantwoordknop").innerHTML = 'Beantwoord';

            }
            document.getElementById("motivatie").innerHTML = data.motivatie;
            document.getElementById("categorie_volgende_vraag").value = data.categorie_volgende_vraag;
            kennismatrix = data.kennismatrix;
            let oudetekst = document.getElementById("kennismatrix").innerHTML;
           document.getElementById("kennismatrix").innerHTML = 
            data.kennismatrix.map((item, i) => {
                const key = Object.keys(item)[0];
                const fields = item[key];
                // Maak een lijstje van alle key-value paren binnen dit onderwerp
                const details = Object.entries(fields)
                .map(([field, value]) => `${field}: ${value} - `)
                .join("");
                return `<div>
                <b>${key}</b>: ${details}
                </div>`;
            }).join("");
            document.getElementById("kennismatrix").innerHTML += "--<br>";
            document.getElementById("kennismatrix").innerHTML += oudetekst;
}
        function mt_beantwoord_vraag(elem, antwoordp, correct){
            let titeljouwantwoord = document.getElementById("titeljouwantwoord");
            titeljouwantwoord.innerHTML = 'Wachten op volgende vraag!';
            titeljouwantwoord.style.color = 'red';
            let buttons = document.getElementsByClassName("antwoordbuttons");
            for(let x = 0; x < buttons.length; x++){
                buttons[x].onclick = ()=>alert("we wachten op de volgende vraag");
            }
            elem.style.backgroundColor = correct ? 'lightgreen' : 'salmon';
            const user_id = document.getElementById("kandidaatnr").value;
            const vraag = document.getElementById("vraag").innerHTML;
            const antwoord = antwoordp;
            const categorie = document.getElementById("categorie_volgende_vraag").value;
            const sessie_id = 1;
            let verzendObject = JSON.stringify({user_id, vraag, antwoord, categorie, sessie_id});
            post_fetch("/vraag_invoeren",verzendObject, mt_start_systeem);

        }
function toonAntwoordKnoppen(data){
    let letters= [data.antwoorda,data.antwoordb,data.antwoordc,data.antwoordd];
    let antwoordletter = ["a", "b", "c", "d"]
    let returnString = "";
    for(let x = 0; x<4; x++){
        console.log(data.correct_antwoord)
        if(letters[x] != "undefined"){
            returnString += `<div><button class="antwoordbuttons" onclick="mt_beantwoord_vraag(this, '${letters[x]}', ${antwoordletter[x] == data.correct_antwoord})">${antwoordletter[x]}) ${letters[x]}</button></div><br>`
        }
    }    
    return returnString;
}
function maakrapportage(){
    console.log("maak rapportage");
        const kandidaatnr = document.getElementById("kandidaatnr").value;
    const opleidingsnr = document.getElementById("opleidingsnr").value;
    let verzendObject = JSON.stringify({kandidaatnr, opleidingsnr, kennismatrix});
    post_fetch("/mt_maak_rapportage",verzendObject, mt_verwerk_rapportage);
}

function mt_verwerk_rapportage(data){
    document.getElementById("antwoord").innerHTML = data.rapportage;
}