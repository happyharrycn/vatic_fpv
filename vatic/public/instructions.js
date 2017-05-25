function instructions(job, h)
{
    h.append("<h1>Important Instructions</h1>");
    h.append("<p>In this task, we ask you to annotate a video. You are to mark the 'Start' and 'End' of an action in the video. These instructions will give you tips on how to best use our tool.</p>");
    h.append("<p>Please watch the below video (and/or read the below section) for instructions:</p>");
    h.append('<iframe width="640" height="360" src="http://www.youtube.com/embed/K8wSD_s8Ucg" frameborder="0" allowfullscreen></iframe>');

    h.append('<p></p>');
    h.append("<img src='action.jpg' align='right' style='border:2px solid black; border-style: inset'>");
    h.append("<h2>Crash Course</h2>");
    var str = "<ul>";
    str += "<li>There will be only one instance of the specified action in the video shown.</li>";
    str += "<li>Make your action interval as tight as possible.</li>";
    str += "<li>Start of the action should always precede the End.</li>";
    str += "<li>The minimum separation between Start and End frames is 10.</li>";
    if (job.perobject > 0)
    {
        var amount = Math.floor(job.perobject * 100);
        str += "<li>We will pay you <strong>" + amount + "&cent; for each object</strong> you annotate.</li>";
    }
    if (job.completion > 0)
    {
        var amount = Math.floor(job.completion * 100);
        str += "<li>We will award you a <strong>bonus of " + amount + "&cent; if you annotate every object</strong>.</li>";
    }
    if (job.skip > 0)
    {
        str += "<li>When the video pauses, adjust your annotations.</li>";
    }
    str += "<li>We will hand review your work.</li>";
    str += "<li>Sometimes the action specified could be partially occluded in the video.</li>";
    str += "</ul>";
    h.append(str);

    h.append("<h2>Getting Started</h2>");
    h.append("<p>Press the <strong>Play</strong> button to play the video.</p>");
    h.append("<p><strong>Pause</strong> the video when you reach the frame in which the specified action begins.</p>");
    h.append("<p>Click the <strong>Start</strong> button to mark the 'Start' of the action. </p>");

    h.append("<img src='label.jpg' align='right' style='border:2px solid black; border-style: inset'>");
    h.append("<p>On the right, directly below the Start button, you will find a colorful box. The box shows you the frame number corresponding to the 'Start' or 'Stop' of the action you just annotated.</p>");

    if (job.skip > 0)
    {
        h.append("<p>Press the <strong>Play</strong> button. The video will play.</p>");
    }
    else
    {
        h.append("<p>Press the <strong>Play</strong> button. The video will begin to play forward. </p>");
    }

    h.append("<img src='boxes.jpg' align='right' style='border:2px solid black; border-style: inset'>");
    h.append("<p>Similarly, click the <strong>End</strong> button to mark the 'End' of the action.</p>");
    h.append("<p>Boxes will appear below the video to provide information about the temporal location of 'Start' and 'End' along the player slider.</p>");
    
    h.append("<img src='submit.jpg' align='right' style='border:2px solid black; border-style: inset'>");
    h.append("<p>When you are ready to submit your work, rewind the video and watch it through one more time. Do the 'Start' and 'End' of action you specified cover the complete action? After you have checked your work, press the <strong>Submit HIT</strong> button. We will pay you as soon as possible.</p>");

    h.append("<h2>How We Accept Your Work</h2>");
    h.append("<p>We will hand review your work and we will only accept high quality work. Your annotations are not compared against other workers. Follow these guidelines to ensure your work is accepted:</p>");
    
    h.append("<h3>Mark both Start and End of the action</h3>")
    h.append("<p>Press the <strong>Play</strong> button. The video will play.</p>");
    h.append("<p>Pause the video when you reach the frame where the action starts. Adjust the player slider to go to the exact frame in which the action starts</p>");
    h.append("<p>Now click the <strong>Start</strong> button to mark the 'Start' of the action specified in the right hand column beside the video. </p>");
    h.append("<p>To check if the 'Start' label was marked on the correct frame, drag the video player slider to a frame where you think the action started, and verify if the frame number specified on the colorful box on the right and the current frame number shown beside the video player's slider are the same.</p>");
    h.append("<p>The Start and End buttons will be disabled after they have been marked in the video.</p>");
    h.append("<img src='delete.jpg' align='right' style='border:2px solid black; border-style: inset'>");
    h.append("<p>If you want to make changes to an annotation, <strong>delete</strong> the existing one by clicking the 'Delete' icon on the top right corner of the colorful boxes on the right, and create a new annotation in the correct frame.</p>");

    //h.append("<img src='secret.png'>");
    //h.append("<img src='everyobject.jpg'>");

    h.append("<strong>Ensure that Start and End are in order, and at a minimum separation of 10 frames.</strong>");

    h.append("<h2>Advanced Features</h2>");
    h.append("<p>We have provided some advanced tools for videos that are especially difficult. Clicking the <strong>Options</strong> button will enable the advanced options.</p>");
    h.append("<ul>" +
        "<li>Clicking <strong>Hide Boxes?</strong> will temporarily hide the boxes on the screen. This is useful when the scene becomes too crowded. Remember to click it again to show the boxes again!</li>" +
        "<li>The <strong>Slow</strong>, <strong>Normal</strong>, <strong>Fast</strong> buttons will change how fast the video plays back. If the video becomes confusing, slowing the play back speed may help.</li>" +
    "</ul>");

    h.append("<h3>Keyboard Shortcuts</h3>");
    h.append("<p>These keyboard shortcuts are available for your convenience:</p>");
    h.append('<ul class="keyboardshortcuts">' +
        '<li><code>t</code> toggles play/pause on the video</li>' +
        '<li><code>r</code> rewinds the video to the start</li>' +
        '<li><code>h</code> hides/shows the boxes (only after clicking Options button)</li>' +
        '<li><code>d</code> jump the video forward a bit</li>' +
        '<li><code>f</code> jump the video backward a bit</li>' +
        '<li><code>v</code> step the video forward a tiny bit</li>' +
        '<li><code>c</code> step the video backward a tiny bit</li>' +
        '</ul>');
}
