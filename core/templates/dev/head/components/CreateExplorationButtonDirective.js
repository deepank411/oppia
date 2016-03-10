// Copyright 2016 The Oppia Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview Directive for the Create Exploration Button.
 *
 * @author sean@seanlip.org (Sean Lip)
 */

oppia.directive('createExplorationButton', [function() {
  return {
    restrict: 'E',
    templateUrl: 'components/createExplorationButton',
    controller: [
      '$scope', '$timeout', '$window', 'ExplorationCreationButtonService',
      'siteAnalyticsService', 'CATEGORY_LIST',
      function(
          $scope, $timeout, $window, ExplorationCreationButtonService,
          siteAnalyticsService, CATEGORY_LIST) {
        $scope.showCreateExplorationModal = function() {
          ExplorationCreationButtonService.showCreateExplorationModal(
            CATEGORY_LIST);
        };
        $scope.showUploadExplorationModal = function() {
          ExplorationCreationButtonService.showUploadExplorationModal(
            CATEGORY_LIST);
        };

        $scope.onRedirectToLogin = function(destinationUrl) {
          siteAnalyticsService.registerStartLoginEvent(
            'createExplorationButton');
          $timeout(function() {
            $window.location = destinationUrl;
          }, 150);
          return false;
        };
      }
    ]
  };
}]);
