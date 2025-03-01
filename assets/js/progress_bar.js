document.addEventListener('DOMContentLoaded', function () {
    // Example JSON data for a single bill
    const bill = {
        "Bill_Sponsor": "John Doe",
        "Bill_Number": "HB123",
        "Bill_Title": "Example Bill",
        "Description": "This is an example bill description.",
        "Process_Tag": "Floor Vote 2.3", // Change this for different bills
        "Day_of_Legislature": "15",
        "Read": "Neutral",
        "Img_URL": "https://via.placeholder.com/150",
        "Webpage": "https://example.com"
    };

    // Define all possible process steps
    const processTags = [
        "Rules 1", "Committee 1", "Floor Vote 1.1", "Floor Vote 1.2", "Floor Vote 1.3",
        "Rules 2", "Committee 2", "Floor Vote 2.1", "Floor Vote 2.2", "Floor Vote 2.3",
        "Governor", "Bill Passed", "Concurrence", "Graveyard", "Vetoed"
    ];

    // Get the index of the bill's current process step
    const currentStepIndex = processTags.indexOf(bill.Process_Tag);
    const totalSteps = processTags.length;
    const progressPercentage = (currentStepIndex / (totalSteps - 1)) * 100; // Calculate progress

    // Create a div for the bill
    const billCard = document.createElement("div");
    billCard.classList.add("bill-card");
    billCard.style.border = "3px solid " + getColorForReadValue(bill.Read);
    billCard.style.padding = "10px";
    billCard.style.margin = "5px 0";
    billCard.style.borderRadius = "5px";

    billCard.innerHTML = `
        <h4 style="background-color: ${getColorForReadValue(bill.Read)}; color: white; padding: 5px; border-radius: 5px 5px 0 0; margin: -10px -10px 10px -10px; text-align: center;">
            ${bill["Bill_Number"]}: ${bill["Bill_Title"]}
        </h4>
        <p>${bill.Description}</p>
        <p><strong>Status:</strong> ${bill["Process_Tag"]}</p>

        <!-- Progress Bar -->
        <div style="background-color: #e0e0e0; border-radius: 25px; height: 30px; width: 100%; margin: 10px 0;">
            <div id="progress-bar" style="height: 100%; width: ${progressPercentage}%; background-color: ${getProgressColor(progressPercentage)}; border-radius: 25px;"></div>
        </div>

        <!-- Progress Percentage Label -->
        <p style="text-align: center; font-weight: bold;">Progress: ${Math.round(progressPercentage)}%</p>

        <p><strong>Day of Legislature:</strong> ${bill["Day_of_Legislature"]}</p>
    `;

    // Append the bill card to the container
    const billsContainer = document.getElementById("billsContainer");
    billsContainer.appendChild(billCard);
});

// Function to determine color based on "Read" value
function getColorForReadValue(readValue) {
    const colors = {
        "Positive": "#4CAF50",
        "Neutral": "#FFC107",
        "Negative": "#F44336"
    };
    return colors[readValue] || "#9E9E9E"; // Default to gray if unknown
}

// Function to dynamically change the progress bar color based on the progress
function getProgressColor(progress) {
    if (progress < 25) return "#F44336"; // Red for early stages
    if (progress < 50) return "#FFC107"; // Yellow for middle stages
    if (progress < 75) return "#4CAF50"; // Green for near completion
    return "#4CAF50"; // Fully green at 100%
}
