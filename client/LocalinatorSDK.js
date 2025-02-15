// LocalinatorSDK.js

// Default base URL (can be overridden later)
let baseURL_ahgjfh = "http://localhost:8080/";

// Function to set a new base URL if needed
function setBaseURL(newURL) {
    baseURL_ahgjfh = newURL;
}

// Function to get the current base URL (useful if needed)
function getBaseURL() {
    return baseURL_ahgjfh;
}

// Function to build the API URL dynamically using the base URL
function buildAPIURL(location) {
    return `${baseURL_ahgjfh}${location}`;
}

// Example: Use this in your application to update and retrieve the base URL
// setBaseURL("https://newapi.example.com/api/");
// let apiURL = buildAPIURL("path/to/endpoint");
// console.log(apiURL);  // "https://newapi.example.com/api/path/to/endpoint"


