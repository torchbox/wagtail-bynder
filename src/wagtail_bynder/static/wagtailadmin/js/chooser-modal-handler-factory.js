class BynderChooserModalOnloadHandlerFactory {
  constructor(opts) {
    this.bynderDomain = opts?.bynderDomain || window.bynderDomain;
    this.bynderAPIToken = opts?.bynderAPIToken || window.bynderAPIToken;
    this.chooseStepName = opts?.chooseStepName || 'choose';
    this.chosenStepName = opts?.chosenStepName || 'chosen';
    this.chosenResponseName = opts?.chosenResponseName || 'chosen';
    this.searchController = null;
    this.assetType = opts?.assetType || null;
    this.chosenMultipleUrl = opts?.chosenMultipleUrl || "/";
    this.chosenSingleUrl = opts?.chosenSingleUrl || "/";
    this.chosenUrlAppendSlash = window.chosenUrlappendSlash || true;
  }

  onLoadChooseStep(modal) {
    this.initBynderCompactView(modal);
  }

  onLoadChosenStep(modal, jsonData) {
    modal.respond(this.chosenResponseName, jsonData.result);
    modal.close();
  }

  onLoadErrorStep(modal, jsonData) {
    // Display error message in the modal
    $(modal.body).append(
      '<div class="help-block help-critical">' +
        '<strong>' +
        gettext('Server Error') +
        ': </strong>' +
        jsonData.error_message +
        '</div>',
    );
    // Re-initialize the Bynder view so user can try again
    this.initBynderCompactView(modal);
  }

  initBynderCompactView(modal) {
    // NOTE: This div is added to the template:
    // wagtailadmin/chooser/choose-bynder.html template
    const compactViewContainer = $("#bynderCompactView", modal.body).get(0); /* eslint-disable-line no-undef */

    // Copy variables from the class to allow access in functions
    const { chosenMultipleUrl, chosenSingleUrl } = this;

    const config = {
      language: "en_US",
      container: compactViewContainer,
      mode: "SingleSelect",
      portal: {
        url: this.bynderDomain,
        editable: false
      },
      hideLimitedUse: true,
      onSuccess: function(assets, additionalInfo) {  // eslint-disable-line
        let url = "";
        const params = {};
        if(assets.length > 1) {
          params.ids = [];
          for (let i = 0; i < assets.length; i++) {  // eslint-disable-line
            params.ids.append(assets[i].databaseId);
          }
          url = chosenMultipleUrl;
        }
        else {
          url = chosenSingleUrl + assets[0].databaseId;
          if (chosenUrlAppendSlash) {
            url += "/";
          }
        }
        modal.loadUrl(url, params);
        return false;
      }
    }
    if(this.bynderAPIToken){
        config.authentication = {
            getAccessToken: () => this.bynderAPIToken,
            hideLogout: true
        };
    }
    if(this.assetType){
        config.assetTypes = [this.assetType];
    }
    window.BynderCompactView.open(config);
  }

  getOnLoadHandlers() {
    return {
      [this.chooseStepName]: (modal, jsonData) => {
          this.onLoadChooseStep(modal, jsonData);
      },
      [this.chosenStepName]: (modal, jsonData) => {
          this.onLoadChosenStep(modal, jsonData);
      },
      error: (modal, jsonData) => {
          this.onLoadErrorStep(modal, jsonData);
      },
    };
  }
}

window.BynderChooserModalOnloadHandlerFactory = BynderChooserModalOnloadHandlerFactory;
