const videoChooserModalOnloadHandlers = new window.BynderChooserModalOnloadHandlerFactory({
  assetType: "video",
  chosenMultipleUrl: `${window.videoChosenBaseUrl}chosen-multiple/`,
  chosenSingleUrl: `${window.videoChosenBaseUrl}chosen/`,
}).getOnLoadHandlers();

class VideoChooserModal {
  onloadHandlers = videoChooserModalOnloadHandlers;

  // identifier for the ModalWorkflow response that indicates an item was chosen
  chosenResponseName = 'chosen';

  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  getURL(opts) {
    return this.baseUrl;
  }

  // eslint-disable-next-line
  getURLParams(opts) {
    const urlParams = {};
    if (opts.multiple) {
      urlParams.multiple = 1;
    }
    return urlParams;
  }

  open(opts, callback) {
    // eslint-disable-next-line no-undef
    ModalWorkflow({
      url: this.getURL(opts || {}),
      urlParams: this.getURLParams(opts || {}),
      onload: this.onloadHandlers,
      responses: {
        [this.chosenResponseName]: (result) => {
          callback(result);
        },
      },
    });
  }
}

window.VideoChooserModal = VideoChooserModal;
