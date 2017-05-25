/*
*
* This readme pertains only to the changes made to support action annotation using VATIC.
*
*/

The modified interface allows videos to be labeled with action annotations by marking the 'Start' and 'End' of an action. (See attached interface.png)

List of modified files:
	turkic/turkic/
		cli.py
	vatic/
		cli.py  models.py
	vatic/public/
		instructions.js  job.js  objectui.js  tracks.js  ui.js  videoplayer.js


Misc changes made to:
	- load videos as a single segment
	- list jobs sorted by time
	- list all incomplete jobs


Matlab code to read annotations:
         load(['temporalannotations.mat']);
	 startaction = 0 ; endaction = 0;
         for m = 1:numel(annotations)
             if ( numel(annotations{m}.attributes) > 0 && strcmp(annotations{m}.attributes{1}.text, 'Start') == 1 && startaction == 0 )
                 startaction = double(annotations{m}.frame);
             end
             if ( numel(annotations{m}.attributes) > 0 && strcmp(annotations{m}.attributes{1}.text, 'End') == 1 && endaction == 0 )
                 endaction = double(annotations{m}.frame);
             end
         end


If you use this software, please cite:
Active Learning of an Action Detector from Untrimmed Videos.  Sunil Bandla and Kristen Grauman.  In Proceedings of the IEEE International Conference on Computer Vision (ICCV), Sydney, Australia, December 2013.

@inproceedings{ICCV2013_active_untrimmed,
    author = "Sunil Bandla and Kristen Grauman",
    title = "Active Learning of an Action Detector from Untrimmed Videos.",
    booktitle = "IEEE International Conference on Computer Vision (ICCV)",
    year = "2013"
}

--
Original authors of this software:

Carl Vondrick, Donald Patterson, Deva Ramanan. "Efficiently Scaling Up Crowdsourced Video Annotation" International Journal of Computer Vision (IJCV). June 2012. 

http://web.mit.edu/vondrick/vatic/

---
Please direct any questions to:
	Sunil Bandla
	bsunil@utexas.edu

