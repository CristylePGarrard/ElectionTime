fetch('https://raw.githubusercontent.com/CristylePGarrard/ElectionTime/refs/heads/gh-pages/assets/reps.json') // Update with the actual path
  .then(response => response.json())
  .then(data => {
    const container = document.getElementById('cards-container'); // Update with your actual container ID
    const officeType = document.body.dataset.office; // Set a data attribute in your HTML to specify office type

    data.filter(rep => rep.Office === officeType).forEach(rep => {
      const card = document.createElement('div');
      card.className = 'card mb-3 mx-2 row';
      card.style.maxWidth = '16rem';
      card.style.backgroundColor = '#a8e3f0';
      card.id = rep.Img_ID;

      card.innerHTML = `
        <div class="col">
            <img src="${rep.Img_URL}" class="card-img-top pt-2" alt="Image of ${rep.Rep_Name} from utah.gov website">
            <div class="card-body">
                <h5 class="card-title">${rep.Rep_Name}</h5>
                <h6 class="card-subtitle mb-2 text-body-secondary mx-2">District: ${rep.District}</h6>
                <h6 class="card-subtitle mb-2 text-body-secondary mx-2">Party: ${rep.Party}</h6>
                <h6 class="card-subtitle mb-2 text-body-secondary mx-2">County(ies): ${rep['County(ies)']}</h6>
                <h6 class="card-subtitle mb-2 text-body-secondary mx-2">Email: <a href="mailto:${rep.Email}">${rep.Email}</a></h6>
                <p>
                    <button class="btn btn-primary" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${rep.Img_ID}" aria-expanded="false" aria-controls="collapse-${rep.Img_ID}">
                        More Info
                    </button>
                </p>
            </div>
        </div>
        <div class="col">
            <div>
                <div class="col collapse collapse-horizontal pb-2" id="collapse-${rep.Img_ID}">
                    <div class="card card-body" style="min-width: 13rem;">
                        <a href="${rep.Webpage}" class="card-link" target="_blank">Gov Website</a>
                        <a href="${rep.Legislation_By_Representative}" class="card-link" target="_blank">Legislation</a>
                    </div>
                </div>
            </div>
        </div>
      `;
      container.appendChild(card);
    });
  })
  .catch(error => console.error('Error loading JSON:', error));
