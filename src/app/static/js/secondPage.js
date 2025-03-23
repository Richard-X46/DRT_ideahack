// Fetch locations from locations.geojson
fetch('/static/data/locations.geojson')  // Ensure the path is correct
    .then(response => response.json())
    .then(data => {
        const sourceDatalist = document.getElementById('source-locations');
        const destinationDatalist = document.getElementById('destination-locations');

        // Populate the datalists with locations
        data.features.forEach(location => {
            const locationName = location.properties.name;  // Assuming "name" holds the location name

            // Create an option for source
            const sourceOption = document.createElement('option');
            sourceOption.value = locationName;
            sourceDatalist.appendChild(sourceOption);

            // Create an option for destination (copy the source option for simplicity)
            const destinationOption = document.createElement('option');
            destinationOption.value = locationName;
            destinationDatalist.appendChild(destinationOption);
        });
    })
    .catch(error => console.error("Error loading the JSON data:", error));

// Add event listener for the Get Map button
// Add event listener for the Get Map button
document.getElementById("getMapBtn").addEventListener("click", function() {
    const source = document.getElementById("source").value;
    const destination = document.getElementById("destination").value;

    if (!source || !destination) {
        alert("Please select both source and destination.");
        return;
    }

    // Send a POST request to FastAPI to get the map
    fetch('/get_map', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            source: source,
            destination: destination
        })
    })
    .then(response => {
        console.log(response);  // Check the response object
        return response.text();
    })
    .then(data => {
        console.log(data);  // Debugging line to see the response from FastAPI
        const mapContainer = document.getElementById('map-container');
        mapContainer.innerHTML = data;  // Inject the map HTML into the container
    })
    .catch(error => {
        console.error("Error fetching the map:", error);
        alert("Failed to load the map.");
    });
});
