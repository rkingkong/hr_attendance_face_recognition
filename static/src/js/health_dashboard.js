odoo.define('hr_attendance_face_recognition.health_dashboard', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');
var ajax = require('web.ajax');

var QWeb = core.qweb;
var _t = core._t;

var FaceHealthDashboard = AbstractAction.extend({
    template: 'face_recognition_health_dashboard',
    
    events: {
        "click #refresh_cache": function() { this._refreshCache(); },
        "click #run_diagnostics": function() { this._runDiagnostics(); },
        "click #test_kiosk": function() { this._testKiosk(); },
    },
    
    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.updateInterval = null;
        this.lastUpdateTime = new Date();
    },
    
    willStart: function () {
        return this._super.apply(this, arguments);
    },
    
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._fetchHealthData();
            
            // Set up auto-refresh every 2 minutes
            self.updateInterval = setInterval(function() {
                self._fetchHealthData();
            }, 120000);
        });
    },
    
    destroy: function () {
        // Clear the update interval when component is destroyed
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        this._super.apply(this, arguments);
    },
    
    _fetchHealthData: function() {
        var self = this;
        
        // Call the health check endpoint
        this._rpc({
            route: '/face_recognition/health',
            params: {}
        }).then(function(result) {
            self._updateDashboard(result);
            self.lastUpdateTime = new Date();
            $("#last_updated").text(self.lastUpdateTime.toLocaleTimeString());
        }).catch(function(error) {
            console.error('Error fetching health data:', error);
            self._showError("Could not fetch health data. Please check server logs.");
        });
    },
    
    _updateDashboard: function(data) {
        // Update overall status indicator
        var statusClass = 'success';
        if (data.status === 'warning') {
            statusClass = 'warning';
        } else if (data.status === 'error') {
            statusClass = 'danger';
        }
        
        $('#status_indicator').removeClass('bg-success bg-warning bg-danger').addClass('bg-' + statusClass);
        $('#status_indicator').html('<i class="fa fa-' + (data.status === 'ok' ? 'check' : 'exclamation-triangle') + '"></i>');
        $('#status_text').text(data.status === 'ok' ? 'System Healthy' : 'Issues Detected');
        
        // Update status details
        var detailsHtml = '';
        for (var key in data.checks) {
            var check = data.checks[key];
            var checkClass = check.status === 'ok' ? 'success' : (check.status === 'warning' ? 'warning' : 'danger');
            var icon = check.status === 'ok' ? 'check-circle' : 'exclamation-triangle';
            
            detailsHtml += '<div class="o_face_check_item">';
            detailsHtml += '<span class="o_face_check_icon text-' + checkClass + '"><i class="fa fa-' + icon + '"></i></span>';
            detailsHtml += '<span class="o_face_check_name">' + this._formatCheckName(key) + '</span>';
            detailsHtml += '<span class="o_face_check_message">' + check.message + '</span>';
            detailsHtml += '</div>';
        }
        $('#status_details').html(detailsHtml);
        
        // Update employee stats
        this._updateEmployeeStats(data.checks.database_check);
        
        // Update recognition stats
        this._updateRecognitionStats(data.checks.recognition_performance);
        
        // Update resource stats
        this._updateResourceStats(data.checks.system_check);
    },
    
    _formatCheckName: function(key) {
        // Convert snake_case to Title Case with spaces
        return key.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    },
    
    _updateEmployeeStats: function(data) {
        if (!data) return;
        
        var html = `
            <div class="o_face_stat_item">
                <div class="o_face_stat_label">Total Employees</div>
                <div class="o_face_stat_value">${data.employee_count || 0}</div>
            </div>
            <div class="o_face_stat_item">
                <div class="o_face_stat_label">With Face Data</div>
                <div class="o_face_stat_value">${data.face_registered_count || 0}</div>
            </div>
            <div class="o_face_stat_item">
                <div class="o_face_stat_label">Registration Rate</div>
                <div class="o_face_stat_value">
                    ${data.employee_count ? Math.round((data.face_registered_count / data.employee_count) * 100) : 0}%
                </div>
            </div>
            <div class="o_face_stat_item">
                <div class="o_face_stat_label">Recent Attendance Count</div>
                <div class="o_face_stat_value">${data.recent_face_attendance_count || 0}</div>
            </div>
        `;
        
        $('#employee_stats').html(html);
    },
    
    _updateRecognitionStats: function(data) {
        if (!data) return;
        
        var html = `
            <div class="o_face_stat_item">
                <div class="o_face_stat_label">Average Confidence</div>
                <div class="o_face_stat_value">${data.avg_confidence ? data.avg_confidence.toFixed(2) + '%' : 'N/A'}</div>
            </div>
            <div class="o_face_stat_chart">
                <h5>Confidence Distribution</h5>
                <div class="o_face_confidence_chart">
        `;
        
        // Add confidence distribution bars
        if (data.confidence_distribution && data.confidence_distribution.length > 0) {
            data.confidence_distribution.forEach(function(item) {
                var barClass = 'bg-success';
                if (item.range === 'Below 70%') {
                    barClass = 'bg-danger';
                } else if (item.range === '70-80%') {
                    barClass = 'bg-warning';
                }
                
                html += `
                    <div class="o_face_confidence_bar_container">
                        <div class="o_face_confidence_label">${item.range}</div>
                        <div class="o_face_confidence_bar_wrapper">
                            <div class="o_face_confidence_bar ${barClass}" style="width: ${item.percentage || 0}%"></div>
                        </div>
                        <div class="o_face_confidence_value">${item.count || 0} (${item.percentage ? item.percentage.toFixed(1) : 0}%)</div>
                    </div>
                `;
            });
        } else {
            html += '<div class="text-center">No data available</div>';
        }
        
        html += '</div></div>';
        
        $('#recognition_stats').html(html);
    },
    
    _updateResourceStats: function(data) {
        if (!data) return;
        
        var memoryUsed = data.memory ? this._formatBytes(data.memory.used) : 'N/A';
        var memoryTotal = data.memory ? this._formatBytes(data.memory.total) : 'N/A';
        var diskUsed = data.disk ? this._formatBytes(data.disk.used) : 'N/A';
        var diskTotal = data.disk ? this._formatBytes(data.disk.total) : 'N/A';
        
        var html = `
            <div class="o_face_resource">
                <h5>Memory Usage</h5>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${data.memory && data.memory.percent_used > 90 ? 'bg-danger' : (data.memory && data.memory.percent_used > 70 ? 'bg-warning' : 'bg-success')}" 
                        role="progressbar" 
                        style="width: ${data.memory ? data.memory.percent_used : 0}%;" 
                        aria-valuenow="${data.memory ? data.memory.percent_used : 0}" 
                        aria-valuemin="0" 
                        aria-valuemax="100">
                        ${data.memory ? data.memory.percent_used : 0}%
                    </div>
                </div>
                <div class="o_face_resource_detail">${memoryUsed} / ${memoryTotal}</div>
            </div>
            
            <div class="o_face_resource mt-3">
                <h5>Disk Usage</h5>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${data.disk && data.disk.percent_used > 90 ? 'bg-danger' : (data.disk && data.disk.percent_used > 70 ? 'bg-warning' : 'bg-success')}" 
                        role="progressbar" 
                        style="width: ${data.disk ? data.disk.percent_used : 0}%;" 
                        aria-valuenow="${data.disk ? data.disk.percent_used : 0}" 
                        aria-valuemin="0" 
                        aria-valuemax="100">
                        ${data.disk ? data.disk.percent_used : 0}%
                    </div>
                </div>
                <div class="o_face_resource_detail">${diskUsed} / ${diskTotal}</div>
            </div>
            
            <div class="o_face_resource mt-3">
                <h5>CPU Usage</h5>
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar ${data.cpu && data.cpu.percent_used > 90 ? 'bg-danger' : (data.cpu && data.cpu.percent_used > 70 ? 'bg-warning' : 'bg-success')}" 
                        role="progressbar" 
                        style="width: ${data.cpu ? data.cpu.percent_used : 0}%;" 
                        aria-valuenow="${data.cpu ? data.cpu.percent_used : 0}" 
                        aria-valuemin="0" 
                        aria-valuemax="100">
                        ${data.cpu ? data.cpu.percent_used : 0}%
                    </div>
                </div>
                <div class="o_face_resource_detail">
                    ${data.cpu ? data.cpu.cores + ' cores' : 'N/A'}
                </div>
            </div>
            
            <div class="o_face_system_info mt-3">
                <h5>System Info</h5>
                <div class="o_face_system_detail">
                    ${data.system_info ? data.system_info.platform : 'N/A'}
                </div>
                <div class="o_face_system_detail">
                    Python: ${data.system_info ? data.system_info.python_version.split(' ')[0] : 'N/A'}
                </div>
                <div class="o_face_system_detail">
                    Odoo: ${data.system_info ? data.system_info.odoo_version : 'N/A'}
                </div>
            </div>
        `;
        
        $('#resource_stats').html(html);
    },
    
    _formatBytes: function(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    },
    
    _refreshCache: function() {
        var self = this;
        
        // Show refreshing status
        this._showNotification('Refreshing face recognition cache...', 'info');
        
        // Call the cache refresh endpoint
        this._rpc({
            route: '/face_recognition/cache/refresh',
            params: {}
        }).then(function(result) {
            if (result.success) {
                self._showNotification(result.message, 'success');
                // Refresh dashboard after cache refresh
                self._fetchHealthData();
            } else {
                self._showNotification(result.message || 'Failed to refresh cache', 'danger');
            }
        }).catch(function(error) {
            console.error('Error refreshing cache:', error);
            self._showNotification('Error refreshing cache. Check server logs.', 'danger');
        });
    },
    
    _runDiagnostics: function() {
        var self = this;
        
        // Show diagnostics running status
        this._showNotification('Running face recognition diagnostics...', 'info');
        
        // Call the diagnostics endpoint
        this._rpc({
            route: '/face_recognition/diagnostics',
            params: {}
        }).then(function(result) {
            self._showDiagnosticsResults(result);
        }).catch(function(error) {
            console.error('Error running diagnostics:', error);
            self._showNotification('Error running diagnostics. Check server logs.', 'danger');
        });
    },
    
    _showDiagnosticsResults: function(data) {
        // Generate HTML for diagnostics results
        var html = `
            <div class="o_face_diagnostics">
                <div class="o_face_diagnostics_timestamp">
                    Diagnostics run at: ${new Date(data.timestamp).toLocaleString()}
                </div>
                
                <div class="o_face_issues_container">
                    <h4>Issues Found (${data.issues.length})</h4>
        `;
        
        if (data.issues.length > 0) {
            html += '<div class="o_face_issues_list">';
            
            data.issues.forEach(function(issue) {
                var severityClass = issue.severity === 'error' ? 'danger' : issue.severity;
                
                html += `
                    <div class="o_face_issue_item">
                        <div class="o_face_issue_severity badge badge-${severityClass}">
                            ${issue.severity.toUpperCase()}
                        </div>
                        <div class="o_face_issue_type badge badge-light">
                            ${issue.type}
                        </div>
                        <div class="o_face_issue_message">
                            ${issue.message}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
        } else {
            html += '<div class="alert alert-success">No issues found. System is healthy!</div>';
        }
        
        html += `
                </div>
                
                <div class="o_face_recommendations_container mt-4">
                    <h4>Recommendations (${data.recommendations.length})</h4>
        `;
        
        if (data.recommendations.length > 0) {
            html += '<ul class="o_face_recommendations_list">';
            
            data.recommendations.forEach(function(recommendation) {
                html += `<li>${recommendation}</li>`;
            });
            
            html += '</ul>';
        } else {
            html += '<div class="alert alert-info">No recommendations available.</div>';
        }
        
        html += `
                </div>
            </div>
        `;
        
        // Update and show the diagnostics card
        $('#diagnostics_results').html(html);
        $('#diagnostics_card').show();
        
        // Scroll to the diagnostics card
        $('html, body').animate({
            scrollTop: $('#diagnostics_card').offset().top - 20
        }, 500);
    },
    
    _testKiosk: function() {
        // Navigate to the kiosk page
        window.open('/face_recognition/kiosk', '_blank');
    },
    
    _showNotification: function(message, type) {
        this.displayNotification({
            title: type === 'success' ? _t('Success') : 
                   type === 'warning' ? _t('Warning') : 
                   type === 'info' ? _t('Information') : _t('Error'),
            message: message,
            type: type,
            sticky: false,
        });
    },
    
    _showError: function(message) {
        this._showNotification(message, 'danger');
    }
});

core.action_registry.add('hr_attendance_face_health_dashboard', FaceHealthDashboard);

return FaceHealthDashboard;

});
