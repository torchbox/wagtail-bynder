class VideoChooserFactory {

  widgetClass = window.VideoChooser;

  chooserModalClass = window.VideoChooserModal;

  constructor(html, idPattern, opts = {}) {
    this.html = html;
    this.idPattern = idPattern;
    this.opts = opts;
  }

  render(placeholder, name, id, initialState) {
    const html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
    placeholder.outerHTML = html;
    // eslint-disable-next-line new-cap
    const chooser = new this.widgetClass(id, this.opts);
    chooser.setState(initialState);
    return chooser;
  }

  openModal(callback, customOptions) {
    if (!this.modal) {
      if (!this.opts.modalUrl) {
        throw new Error(
          'ChooserFactory must be passed a modalUrl option if openModal is used',
        );
      }

      // eslint-disable-next-line new-cap
      this.modal = new this.chooserModalClass(this.opts.modalUrl);
    }
    const options = { ...customOptions };
    this.modal.open(options, callback);
  }

  // eslint-disable-next-line class-methods-use-this
  getById(id) {
    /* retrieve the widget object corresponding to the given HTML ID */
    return document.getElementById(`${id}-chooser`).widget;
  }
}


window.telepath.register(
    'wagtail_bynder.widgets.VideoChooser',
    VideoChooserFactory,
);
