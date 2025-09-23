//        const server = 'https://mijnflaskapp.eu.ngrok.io/';
        const server = 'http://127.0.0.1:5000/';
        let kennismatrix = `[]`
        function verstuurantwoord(){
            document.getElementById("beantwoordknop").innerHTML = 'waiting for answer';
            document.getElementById("beantwoordknop").disabled = true;
            const kandidaatnr = document.getElementById("kandidaatnr").value;
            const opleidingsnr = document.getElementById("opleidingsnr").value;
            let verzendObject = JSON.stringify({kandidaatnr, opleidingsnr, kennismatrix});
            post_fetch("/prompt_maken",verzendObject, verwerk_response);
        }
        function beantwoord_vraag(){
            const user_id = document.getElementById("kandidaatnr").value;
            const vraag = document.getElementById("vraag").innerHTML;
            const antwoord = document.getElementById("antwoord").value;
            const categorie = document.getElementById("categorie_volgende_vraag").value;
            const sessie_id = 1;
            let verzendObject = JSON.stringify({user_id, vraag, antwoord, categorie, sessie_id});
            post_fetch("/vraag_invoeren",verzendObject, verstuurantwoord);

        }

        function post_fetch(endpoint, postobject, callback){
            fetch(server+'/'+endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: postobject
            })
            .then(r => {console.log(r);return r.json();})
            .then(d => callback(d))
            .catch(e => {console.log(e);alert('er ging iets mis, ververs de pagina')})

        }
        function verwerk_response(data){
            console.log("hier", data);
            document.getElementById("vraag").innerHTML = data.volgendevraag;
            if(data.volgendevraag == ""){
                alert("het onderzoek is afgerond, u hoeft geen vragen meer te beantwoorden");
                document.getElementById("antwoord").value = 'u hoeft geen vragen meer te beantwoorden';
                document.getElementById("antwoord").disabled = true;
                document.getElementById("beantwoordknop").disabled = true;
            }else{
                document.getElementById("antwoord").value = '';
                document.getElementById("antwoord").disabled = false;
                document.getElementById("beantwoordknop").disabled = false;
                document.getElementById("beantwoordknop").innerHTML = 'Beantwoord';

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
