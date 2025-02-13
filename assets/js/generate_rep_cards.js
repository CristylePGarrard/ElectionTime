let path_to_json = 'https://raw.githubusercontent.com/CristylePGarrard/ElectionTime/refs/heads/gh-pages/assets/reps.json' // Update with the actual path
  fetch(path_to_json)
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('cards-container'); // Update with your actual container ID
      const officeType = document.body.dataset.office; // Set a data attribute in your HTML to specify office type

      data.filter(rep => rep.Office === officeType).forEach(rep => {
        // Define color mapping for parties
        const partyColors = {
          'R': '#F63D23', // Light red (ff9999) for Republicans
          'D': '#0B41F5', // Light blue (9999ff) for Democrats
          'Other': '#a8e3f0' // Default color for other parties
        };

        // Determine card color based on party
        const cardColor = partyColors[rep.Party] || partyColors['Other'];

        const card = document.createElement('div');
        card.className = 'card mb-3 mx-2';
        card.style.maxWidth = '17rem';
        card.style.backgroundColor = cardColor;
        card.id = rep.Img_ID;

        card.innerHTML = `
          <div class="col">
              <img src="${rep.Img_URL}" class="card-img-top pt-2" alt="Image of ${rep.Rep_Name} from utah.gov website">
              <div class="card-body">
                  <h5 class="card-title">${rep.Rep_Name}</h5>
                  <div class='row '>
                  <h6 class="col-6 card-subtitle text-body-secondary">District:</h6>
                  <p class="col card-subtitle text-body-secondary">${rep.District}</p>
                  </div>
                  <div class='row'>
                  <h6 class="col card-subtitle text-body-secondary">County(ies):</h6>
                  <p class="col card-subtitle mb-2 text-body-secondary mx-2">${rep['County(ies)']}</p>
                  </div>
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
                          <h6 class="card-subtitle mb-2 text-body-secondary mx-2">Party: ${rep.Party}</h6>
                          <h6 class="card-subtitle mb-2 text-body-secondary mx-2">Email: <a href="mailto:${rep.Email}">${rep.Email}</a></h6>
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

