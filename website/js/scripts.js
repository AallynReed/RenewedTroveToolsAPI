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
    return getLatestVersionData("https://kiwiapi.slynx.xyz/v1/misc/latest_release").then(
        data => {
            return data;
        }
    );
}

function getDownloadCount() {
    return getLatestVersionData("https://kiwiapi.slynx.xyz/v1/misc/downloads_count").then(
        data => {
            return data;
        }
    );
}

function getLatestDownloadRelease() {
    return getLatestVersionData("https://kiwiapi.slynx.xyz/v1/misc/latest_release/download").then(
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
            version_tags[index].innerHTML = version_tags[index].innerHTML + " " + `<a href="${version.html_url}" target="_blank">${version.tag_name}</a>`; 
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

// function setDownloadReleaseURL() {
//     var download_tags = document.querySelectorAll("a.set-download-release");
//     getLatestDownloadRelease().then(download => {
//         for (index = 0; index < download_tags.length; index++) {  
//             download_tags[index].href = download; 
//         }
//     });
// }

setVersionHtml();
setDownloadCountHtml();
// setDownloadReleaseURL();


  
