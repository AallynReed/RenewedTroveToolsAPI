/*!
* Start Bootstrap - Personal v1.0.1 (https://startbootstrap.com/template-overviews/personal)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-personal/blob/master/LICENSE)
*/
// This file is intentionally blank
// Use this file to add JavaScript to your project

function httpGet(url) {
    return fetch(url)
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .catch(error => {
        console.error('There has been a problem with your fetch operation:', error);
      });
  }

function getLatestVersionData(theUrl) {
    return httpGet(theUrl).then(data => {
        return data;
    });
}

function getLatestVersion() {
    return getLatestVersionData("https://kiwiapi.aallyn.xyz/v1/misc/latest_release").then(
        data => {
            return data;
        }
    );
}

function getDownloadCount() {
    return getLatestVersionData("https://kiwiapi.aallyn.xyz/v1/misc/downloads_count").then(
        data => {
            return data;
        }
    );
}

function getLatestDownloadRelease() {
    return getLatestVersionData("https://kiwiapi.aallyn.xyz/v1/misc/latest_release/download").then(
        data => {
            return data;
        }
    );

}

// Automatics

function setVersionHtml() {
    var version_tags = document.querySelectorAll("span.set-version");
    getLatestVersion().then(version => {
        for (index = 0; index < version_tags.length; index++) {
            const dateObject = new Date(version.created_at);
            const options = { day: '2-digit', month: 'long', year: 'numeric' };
            const formattedDate = dateObject.toLocaleDateString('en-GB', options);
            version_tags[index].innerHTML = version_tags[index].innerHTML + " " + `<a href="${version.html_url}" target="_blank">${version.tag_name}</a><code style="font-size: 14px"> (${formattedDate})</code>`; 
        }
    });
}

function setDownloadCountHtml() {
    var elements = document.querySelectorAll("p.downloads-count");
    getDownloadCount().then(data => {
        for (index = 0; index < elements.length; index++) {  
            elements[index].innerHTML = elements[index].innerHTML + " " + data.downloads; 
        }
    });
}

function hoverBiomeNames(biome) {
    var biome_name = biome.getAttribute("biome");
    var elements = document.querySelectorAll(`[biome="${biome_name}"]`);
    for (index = 0; index < elements.length; index++) {
        var element = elements[index];
        var computedStyle = window.getComputedStyle(element);
        var backgroundColor = computedStyle.backgroundColor;
        if (backgroundColor == "rgba(0, 0, 0, 0)") {
            element.style.background = "rgba(94, 5, 94, 0.48)";
        }
    }
}

function unHoverBiomeNames(biome) {
    var biome_name = biome.getAttribute("biome");
    var elements = document.querySelectorAll(`[biome="${biome_name}"]`);
    for (var index = 0; index < elements.length; index++) {
        var element = elements[index];
        var computedStyle = window.getComputedStyle(element);
        var backgroundColor = computedStyle.backgroundColor;
        if (backgroundColor == "rgba(94, 5, 94, 0.48)") {
            element.style.background = "transparent";
        }
    }
}


function clickBiomeName(biome) {
    var computedStyle = window.getComputedStyle(biome);
    var backgroundColor = computedStyle.backgroundColor;
    if (backgroundColor == "rgba(5, 94, 94, 0.48)") {
        var elements = document.querySelectorAll(`pill`);
        for (index = 0; index < elements.length; index++) {
            elements[index].style.background = "";
        }
        var elements = document.querySelectorAll(`td`);
        for (index = 0; index < elements.length; index++) {
            elements[index].style.background = "";
        }
        return;
    }
    var biome_name = biome.getAttribute("biome");
    var elements = document.querySelectorAll(`pill`);
    for (index = 0; index < elements.length; index++) {
        if (elements[index].getAttribute("biome") != biome_name) {
            elements[index].style.background = "";
        } else {
            elements[index].style.background = "rgba(5, 94, 94, 0.48)";
        }
    }
    var elements = document.querySelectorAll(`td`);
    for (index = 0; index < elements.length; index++) {
        if (elements[index].getAttribute("biome") != biome_name) {
            elements[index].style.background = "";
        } else {
            elements[index].style.background = "rgba(5, 94, 94, 0.48)";
        }
    }
}

function hoverBiomeIcons(biome) {
    var biome_name = biome.getAttribute("biome_icon");
    var elements = document.querySelectorAll(`[biome_icon="${biome_name}"]`);
    for (index = 0; index < elements.length; index++) {
        var element = elements[index];
        var computedStyle = window.getComputedStyle(element);
        var backgroundColor = computedStyle.backgroundColor;
        if (backgroundColor == "rgba(0, 0, 0, 0)") {
            element.style.background = "rgba(94, 5, 94, 0.48)";
        }
    }
}

function unHoverBiomeIcons(biome) {
    var biome_name = biome.getAttribute("biome_icon");
    var elements = document.querySelectorAll(`[biome_icon="${biome_name}"]`);
    for (var index = 0; index < elements.length; index++) {
        var element = elements[index];
        var computedStyle = window.getComputedStyle(element);
        var backgroundColor = computedStyle.backgroundColor;
        if (backgroundColor == "rgba(94, 5, 94, 0.48)") {
            element.style.background = "transparent";
        }
    }
}


function clickBiomeIcon(biome) {
    var computedStyle = window.getComputedStyle(biome);
    var backgroundColor = computedStyle.backgroundColor;
    if (backgroundColor == "rgba(5, 94, 94, 0.48)") {
        var elements = document.querySelectorAll(`pill`);
        for (index = 0; index < elements.length; index++) {
            elements[index].style.background = "";
        }
        var elements = document.querySelectorAll(`td`);
        for (index = 0; index < elements.length; index++) {
            elements[index].style.background = "";
        }
        return;
    }
    var biome_name = biome.getAttribute("biome_icon");
    var elements = document.querySelectorAll(`pill`);
    for (index = 0; index < elements.length; index++) {
        if (elements[index].getAttribute("biome_icon") != biome_name) {
            elements[index].style.background = "";
        } else {
            elements[index].style.background = "rgba(5, 94, 94, 0.48)";
        }
    }
    var elements = document.querySelectorAll(`td`);
    for (index = 0; index < elements.length; index++) {
        if (elements[index].getAttribute("biome_icon") != biome_name) {
            elements[index].style.background = "";
        } else {
            elements[index].style.background = "rgba(5, 94, 94, 0.48)";
        }
    }
}

function setDateText(element) {
    console.log(element.getAttribute("timestamp"));
    const now = Date.now();
    const date = new Date(parseInt(element.getAttribute("timestamp")));
    // check if now and date are within 10 seconds
    if (Math.abs(now - date) < 10000) {
        element.innerHTML = "Happening now";
        return;
    }
    const months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    const getOrdinalSuffix = (day) => {
        if (day > 3 && day < 21) return 'th'; // Handles 11th, 12th, 13th
        switch (day % 10) {
            case 1: return "st";
            case 2: return "nd";
            case 3: return "rd";
            default: return "th";
        }
    };

    const day = date.getDate();
    const month = months[date.getMonth()];
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');

    const ordinalSuffix = getOrdinalSuffix(day);
    element.innerHTML = `${month}, ${day}${ordinalSuffix} at ${hour}:${minute}`;
}

function setAllDates() {
    var elements = document.querySelectorAll(`td[class="time"]`);
    for (index = 0; index < elements.length; index++) {
        setDateText(elements[index]);
    }
}

window.addEventListener('DOMContentLoaded', (event) => {
    setVersionHtml();
    setDownloadCountHtml();
    setAllDates();
});

// function setDownloadReleaseURL() {
//     var download_tags = document.querySelectorAll("a.set-download-release");
//     getLatestDownloadRelease().then(download => {
//         for (index = 0; index < download_tags.length; index++) {  
//             download_tags[index].href = download; 
//         }
//     });
// }
// setDownloadReleaseURL();

  
