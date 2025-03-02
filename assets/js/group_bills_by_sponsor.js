// Fetch the JSON file and process the data
fetch('assets/bad_bills_combined.json')
  .then(response => response.json())
  .then(data => {
    processBills(data); // Call function to handle the data
  })
  .catch(error => console.error('Error loading the JSON:', error));

function processBills(data) {
    const billsBySponsor = {};
    const processTags = [
        "Rules 1", "Committee 1", "Floor Vote 1.1", "Floor Vote 1.2", "Floor Vote 1.3",
        "Rules 2", "Committee 2", "Floor Vote 2.1", "Floor Vote 2.2", "Floor Vote 2.3",
        "Governor", "Bill Passed", "Concurrence", "Graveyard", "Vetoed"
    ];

    // Group bills by sponsor and keep only the most recent record per bill
    data.forEach(bill => {
        if (!billsBySponsor[bill["Bill_Sponsor"]]) {
            billsBySponsor[bill["Bill_Sponsor"]] = {};
        }

        const currentBill = billsBySponsor[bill["Bill_Sponsor"]][bill["Bill_Number"]];
        if (!currentBill || new Date(currentBill.Date) < new Date(bill.Date)) {
            billsBySponsor[bill["Bill_Sponsor"]][bill["Bill_Number"]] = bill;
        }
    });

    // Sort sponsors by the number of bills they have
    const sortedSponsors = Object.keys(billsBySponsor).sort((a, b) =>
        Object.keys(billsBySponsor[b]).length - Object.keys(billsBySponsor[a]).length
    );

    const billsContainer = document.getElementById("billsContainer");
    billsContainer.innerHTML = ""; // Clear previous content

    sortedSponsors.forEach(sponsor => {
        const sponsorDiv = document.createElement("div");
        sponsorDiv.classList.add("sponsor-section");
        sponsorDiv.style.borderTop = "2px solid black"; // Divider between sponsors
        sponsorDiv.style.marginTop = "20px";
        sponsorDiv.style.paddingTop = "10px";

        const rowDiv = document.createElement("div");
        rowDiv.classList.add("row"); // Create a row for two columns

        // Left column for sponsor details (col-3)
        const leftCol = document.createElement("div");
        leftCol.classList.add("col-12", "col-md-3"); // Make it smaller on larger screens

        // Image, Name, and details
        const sponsorData = billsBySponsor[sponsor][Object.keys(billsBySponsor[sponsor])[0]];  // Get sponsor's first bill for details
        leftCol.innerHTML = `
            <div style="display: flex; justify-content: center;">
                <img src="${sponsorData.Img_URL}" alt="Image of ${sponsor}" class="img-fluid mb-3" style="max-width: 80%; height: auto;">
            </div>
            <h4>${sponsor}</h4>
            <p><strong>District:</strong> ${sponsorData.District}</p>
            <p><strong>County(ies):</strong> ${sponsorData["County(ies)"]}</p>
            <p><strong>Office:</strong> ${sponsorData.Office}</p>
            <p><strong>Website:</strong> <a href="${sponsorData.Webpage}" target="_blank">Visit</a></p>
        `;

        // Right column for the bill cards (col-9)
        const rightCol = document.createElement("div");
        rightCol.classList.add("col-12", "col-md-9"); // Make this larger on larger screens

        Object.values(billsBySponsor[sponsor]).forEach(bill => {
            const billCard = document.createElement("div");
            billCard.classList.add("bill-card");
            billCard.style.border = "3px solid " + getColorForReadValue(bill.Read); // Border color
            billCard.style.padding = "10px";
            billCard.style.margin = "5px 0";
            billCard.style.borderRadius = "5px";

            // Call generateProgressBar to get the progress bar HTML
            const progressBarHTML = generateProgressBar(bill, processTags);

            billCard.innerHTML = `
                <h4 style="background-color: ${getColorForReadValue(bill.Read)}; color: white; padding: 5px; border-radius: 5px 5px 0 0; margin: -10px -10px 10px -10px; text-align: center;">
                    ${bill["Bill_Number"]}: ${bill["Bill_Title"]}
                </h4>
                <p>${bill.Description}</p>
                <p><strong>Status:</strong> ${bill["Process_Tag"]}</p>

                <!-- Progress Bar -->
                ${progressBarHTML}

                <p><strong>Day of Legislature:</strong> ${bill["Day_of_Legislature"]}</p>
            `;

            rightCol.appendChild(billCard);
        });

        rowDiv.appendChild(leftCol); // Add left column to the row
        rowDiv.appendChild(rightCol); // Add right column to the row
        sponsorDiv.appendChild(rowDiv); // Add the row to the sponsor div

        billsContainer.appendChild(sponsorDiv);
    });
}


// Function to generate progress bar based on process tags and bill progress
function generateProgressBar(bill) {
    const progressValue = bill.Progress; // This should be the new 'Progress' column from your dataset
    const progressPercentage = (progressValue / 12) * 100; // Calculate the percentage

    // HTML for progress bar
    return `
        <div style="background-color: #e0e0e0; border-radius: 25px; height: 30px; width: 100%; margin: 10px 0;">
            <div style="height: 100%; width: ${progressPercentage}%; background-color: ${getProgressColor(progressPercentage)}; border-radius: 25px;"></div>
        </div>
        <p style="text-align: center; font-weight: bold;">Progress: ${Math.round(progressPercentage)}%</p>
    `;
}

// Function to get the color based on the percentage of progress
function getProgressColor(progress) {
    if (progress <= 45) return '#FF5733';  // Red
    if (progress <= 85) return '#FFC300';  // Yellow
    return '#4CAF50';  // Green
}


// Function to determine color based on "Read" value
function getColorForReadValue(readValue) {
    const colors = {
        "Positive": "#4CAF50",
        "Neutral": "#FFC107",
        "Negative": "#F44336"
    };
    return colors[readValue] || "#9E9E9E"; // Default to gray if unknown
}