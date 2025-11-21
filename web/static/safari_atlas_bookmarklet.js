// Safari Bookmarklet: Send to Atlas v3
// Drag this link to Safari bookmarks: javascript:(function(){/* CODE BELOW */})();

javascript:(function(){
    var url = window.location.href;
    var atlasUrl = 'http://atlas.khamel.com:35555/ingest?url=' + encodeURIComponent(url);

    // Create invisible iframe to send to Atlas
    var iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = atlasUrl;
    document.body.appendChild(iframe);

    // Remove iframe after 2 seconds
    setTimeout(function(){
        document.body.removeChild(iframe);
        alert('URL sent to Atlas!');
    }, 2000);
})();