class UnitsRouter {
	orgTeamRe = new RegExp('^#/org/([0-9]+)(:?/team/([0-9]+))?');
	passwdResetRe = new RegExp('^#/password/reset(:?/email/([^/]+)/code/([0-9a-f]+))?');

	new() {
		this.orgId = null;
		this.teamId = null;
		this.email = null;
		this.code = null;
	}

	constructor() {
		this.new();
		this.urlPrefix = '/api/v1';
	}

	setOrg(orgId) {
		this.orgId = orgId;
	}

	setTeam(teamId) {
		this.teamId = teamId;
	}

	setEmail(email) {
		this.email = email;
	}

	setCode(code) {
		this.code = code;
	}

	init() {
		let res = document.location.hash.match(this.orgTeamRe);
		if (res) {
			if (res[1]) {
				this.setOrg(parseInt(res[1]));
			}
			if (res[2]) {
				this.setTeam(parseInt(res[2]));
			}
		}
		res = document.location.hash.match(this.passwdResetRe);
		if (res) {
			this.setOrg(-1);
			if (res[2]) {
				this.setEmail(decodeURIComponent(res[2]));
			}
			if (res[3]) {
				this.setCode(res[3]);
			}
		}
	}

	getUrl(name) {
		let url = '';

		switch (name) {
			case 'signin':
			case 'teams':
				url += '/org/' + this.orgId;
			case 'password/reset':
				url += '/' + name;
				break;
			case 'team_members':
				url += '/org/' + this.orgId + '/team/' + this.teamId + '/members';
				break;
			default:
		}

		document.location.hash = url;

		return this.urlPrefix + url;
	}
}


class UnitsConnector {
	constructor(router, messenger) {
		this.router = router;
		this.messenger = messenger;
		this.email = null;
		this.token = null;
	}
}


class UnitsMessenger {
	constructor() {
	}

	postError(msg) {
		const parent = document.querySelector('.messenger');
		parent.style.display = 'block';
		parent.innerHTML = msg;
	}

	clearErrors(parent) {
		if (!parent) {
			parent = document.querySelector('.messenger');
		}
		parent.style.display = 'none';
	}
}


const signInHnd = (connector) => {
	const url = connector.router.getUrl('signin');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('POST', url, true);
		xhr.setRequestHeader('Content-Type', 'application/json');
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		}
		xhr.onerror = () => {
			reject(xhr.statusText);
		}
		xhr.send(JSON.stringify({
			email: document.querySelector('#signin-email').value,
			passwd: document.querySelector('#signin-passwd').value
		}));
	});
};


const displayError = (connector, reason) => {
	let msg = '';
	for (let key in reason) {
		let obj = reason[key];
		if (Array.isArray(obj)) {
			msg += obj.join('<br>');
		} else {
			msg += obj + '<br>';
		}
	}
	connector.messenger.postError(msg);
};


const teamsLoadHnd = (connector) => {
	loadTeamsHnd(connector).then((result) => {
		connector.messenger.clearErrors();
		renderTeamsHnd(connector, result);
	}, (reason) => {
		displayError(connector, reason);
	});
};


const loadTeamsHnd = (connector) => {
	const url = connector.router.getUrl('teams');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('GET', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		}
		xhr.onerror = () => {
			reject(xhr.statusText);
		}
		xhr.send();
	});
};


const teamRemoveFormSubmitHnd = (connector, teamId) => {
	const url = connector.router.getUrl('teams');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('DELETE', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.setRequestHeader('Content-Type', 'application/json');
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		};
		xhr.onerror = () => {
			reject(xhr.statusText);
		};
		xhr.send(JSON.stringify({
			id: teamId
		}));
	});
};


const bindTeamRemoveBtn = (connector, btn) => {
	let teamId = btn.getAttribute('data-team-id');
	btn.addEventListener('click', () => {
		teamRemoveFormSubmitHnd(connector, teamId).then((result) => {
			connector.messenger.clearErrors();
			btn.parentElement.parentElement.remove();
		}, (reason) => {
			displayError(connector, reason);
		});
	});
};


const loadMembersHnd = (connector) => {
	const url = connector.router.getUrl('team_members');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('GET', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		};
		xhr.onerror = () => {
			reject(xhr.statusText);
		};
		xhr.send();
	});
};


const renderMembersHnd = (connector, team_members_data) => {
	const membersList = document.querySelector('.members-list');
	const membersListRows = membersList.querySelectorAll('.row');
	const formOpenBtn = document.querySelector('#member-add-form-show-btn');

	membersList.style.display = 'none';

	Object.entries(membersListRows).map((object) => {
		if (object[1].style.display === 'block' || object[1].style.display === 'flex') {
			object[1].remove();
		}
	});

	const orgLabel = membersList.querySelector('.org-name');
	orgLabel.innerHTML = team_members_data.organization.name;
	orgLabel.addEventListener('click', () => {
		membersList.style.display = 'none';
		teamsLoadHnd(connector);
	});
	membersList.querySelector('.team-name').innerHTML = team_members_data.team.name;

	team_members_data.members.forEach((member) => {
		let row = membersListRows[0].cloneNode(true);
		row.querySelector('.member-email').innerHTML = member.email;
		let btn = row.querySelector('.member-remove-btn');
		btn.setAttribute('data-team-member-id', member.id);
		bindMemberRemoveBtn(connector, btn);
		row.style.display = 'flex';
		formOpenBtn.before(row);
	});

	membersList.style.display = 'block';
};


const memberAddedHnd = (connector, member) => {
	const membersList = document.querySelector('.members-list');
	const membersListRows = membersList.querySelectorAll('.row');
	const formOpenBtn = document.querySelector('#member-add-form-show-btn');

	let row = membersListRows[0].cloneNode(true);
	row.querySelector('.member-email').innerHTML = member.email;
	let btn = row.querySelector('.member-remove-btn');
	btn.setAttribute('data-team-member-id', member.id);
	bindMemberRemoveBtn(connector, btn);
	row.style.display = 'flex';
	formOpenBtn.before(row);
};


const bindTeamMembersBtn = (connector, btn) => {
	let teamId = btn.getAttribute('data-team-id');
	btn.addEventListener('click', () => {
		const teamsList = document.querySelector('.teams-list');
		teamsList.style.display = 'none';
		connector.router.setTeam(teamId);
		loadMembersHnd(connector, teamId).then((result) => {
			connector.messenger.clearErrors();
			renderMembersHnd(connector, result);
		}, (reason) => {
			displayError(connector, reason);
		});
	});
};


const renderTeamsHnd = (connector, teams_data) => {
	const teamsList = document.querySelector('.teams-list');
	const teamsListRows = teamsList.querySelectorAll('.row');
	const formOpenBtn = document.querySelector('#team-add-form-show-btn');

	teamsList.style.display = 'none';

	Object.entries(teamsListRows).map((object) => {
		if (object[1].style.display === 'block' || object[1].style.display === 'flex') {
			object[1].remove();
		}
	});

	teamsList.querySelector('.org-name').innerHTML = teams_data.organization.name;

	teams_data.teams.forEach((team) => {
		let row = teamsListRows[0].cloneNode(true);
		row.querySelector('.team-name').innerHTML = team.name;
		row.querySelector('.team-name').setAttribute('data-team-id', team.id);
		bindTeamMembersBtn(connector, row.querySelector('.team-name'));
		row.querySelector('.team-ctime').innerHTML = team.ctime;
		let btn = row.querySelector('.team-remove-btn');
		btn.setAttribute('data-team-id', team.id);
		bindTeamRemoveBtn(connector, btn);
		row.style.display = 'flex';
		formOpenBtn.before(row);
	});

	teamsList.style.display = 'block';
};


const teamAddedHnd = (connector, team) => {
	const teamsList = document.querySelector('.teams-list');
	const teamsListRows = teamsList.querySelectorAll('.row');
	const formOpenBtn = document.querySelector('#team-add-form-show-btn');

	let row = teamsListRows[0].cloneNode(true);
	row.querySelector('.team-name').innerHTML = team.name;
	row.querySelector('.team-name').setAttribute('data-team-id', team.id);
	bindTeamMembersBtn(connector, row.querySelector('.team-name'));
	row.querySelector('.team-ctime').innerHTML = team.ctime;
	let btn = row.querySelector('.team-remove-btn');
	btn.setAttribute('data-team-id', team.id);
	bindTeamRemoveBtn(connector, btn);
	row.style.display = 'flex';
	formOpenBtn.before(row);
};


const bindMemberRemoveBtn = (connector, btn) => {
	let teamMemberId = btn.getAttribute('data-team-member-id');
	btn.addEventListener('click', () => {
		memberRemoveFormSubmitHnd(connector, teamMemberId).then((result) => {
			connector.messenger.clearErrors();
			btn.parentElement.parentElement.remove();
		}, (reason) => {
			displayError(connector, reason);
		});
	});
};


const teamAddFormShowHnd = () => {
	const teamForm = document.querySelector('#team-add-form');
	teamForm.style.display = teamForm.style.display === 'block' ? 'none' : 'block';
};


const memberAddFormShowHnd = () => {
	const memberForm = document.querySelector('#member-add-form');
	memberForm.style.display = memberForm.style.display === 'block' ? 'none' : 'block';
};


const teamAddFormSubmitHnd = (connector) => {
	const url = connector.router.getUrl('teams');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('POST', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.setRequestHeader('Content-Type', 'application/json');
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		};
		xhr.onerror = () => {
			reject(xhr.statusText);
		};
		xhr.send(JSON.stringify({
			name: document.querySelector('#team-name').value
		}));
	});
};


const memberAddFormSubmitHnd = (connector) => {
	const url = connector.router.getUrl('team_members');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('POST', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.setRequestHeader('Content-Type', 'application/json');
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		};
		xhr.onerror = () => {
			reject(xhr.statusText);
		};
		xhr.send(JSON.stringify({
			email: document.querySelector('#member-email').value
		}));
	});
};


const memberRemoveFormSubmitHnd = (connector, teamMemberId) => {
	const url = connector.router.getUrl('team_members');
	return new Promise((resolve, reject) => {
		const xhr = new XMLHttpRequest();
		xhr.open('DELETE', url, true);
		xhr.setRequestHeader('Authorization', 'Token ' + connector.token);
		xhr.setRequestHeader('Content-Type', 'application/json');
		xhr.onload = () => {
			const data = JSON.parse(xhr.responseText);
			if (xhr.status == 200) {
				resolve(data);
			} else {
				reject(data);
			}
		};
		xhr.onerror = () => {
			reject(xhr.statusText);
		};
		xhr.send(JSON.stringify({
			id: teamMemberId
		}));
	});
};


window.addEventListener('load', () => {
	const router = new UnitsRouter();
	const messenger = new UnitsMessenger();
	const connector = new UnitsConnector(router, messenger);

	router.init();

	Object.entries(document.querySelectorAll('.team-remove-btn')).map((object) => {
		bindTeamRemoveBtn(connector, object[1]);
	});

	Object.entries(document.querySelectorAll('.member-remove-btn')).map((object) => {
		bindMemberRemoveBtn(connector, object[1]);
	});

	const teamAddFormShowBtn = document.querySelector('#team-add-form-show-btn');
	if (teamAddFormShowBtn) {
		teamAddFormShowBtn.addEventListener('click', teamAddFormShowHnd);
		const teamAddFormSubmitBtn = document.querySelector('#team-add-form-submit-btn');
		if (teamAddFormSubmitBtn) {
			teamAddFormSubmitBtn.addEventListener('click', () => {
				teamAddFormSubmitHnd(connector).then((result) => {
					teamAddFormShowHnd();
					connector.messenger.clearErrors();
					document.querySelector('#team-name').value = '';
					teamAddedHnd(connector, result);
				}, (reason) => {
					displayError(connector, reason);
				});
			});
		}
	}

	const memberAddFormShowBtn = document.querySelector('#member-add-form-show-btn');
	if (memberAddFormShowBtn) {
		memberAddFormShowBtn.addEventListener('click', memberAddFormShowHnd);
		const memberAddFormSubmitBtn = document.querySelector('#member-add-form-submit-btn');
		if (memberAddFormSubmitBtn) {
			memberAddFormSubmitBtn.addEventListener('click', () => {
				memberAddFormSubmitHnd(connector).then((result) => {
					memberAddFormShowHnd();
					connector.messenger.clearErrors();
					document.querySelector('#member-email').value = '';
					memberAddedHnd(connector, result);
				}, (reason) => {
					displayError(connector, reason);
				});
			});
		}
	}

	const signinBox = document.querySelector('.signin');

	Object.entries(document.querySelectorAll('.signout')).map((object) => {
		object[1].addEventListener('click', () => {
			Object.entries(document.querySelectorAll('.box')).map((_object) => {
				_object[1].style.display = 'none';
			});
			connector.token = null;
			document.querySelector('#signin-email').value = '';
			document.querySelector('#signin-passwd').value = '';
			signinBox.style.display = 'block';
		});
	});

	const passwdResetReqBox = document.querySelector('.password-rst-req');
	const passwdResetReqLnk = document.querySelector('.password-rst');
	const passwdResetReqBoxShow = () => {
		signinBox.style.display = 'none';
		passwdResetReqBox.style.display = 'block';
		document.querySelector('#password-rst-req-email').value = document.querySelector('#signin-email').value;
	};
	if (passwdResetReqLnk) {
		passwdResetReqLnk.addEventListener('click', passwdResetReqBoxShow);
	}
	if (passwdResetReqBox) {
		const passwdResetReqSubmitBtn = document.querySelector('#password-rst-req-form-submit-btn');
		if (passwdResetReqSubmitBtn) {
			passwdResetReqSubmitBtn.addEventListener('click', () => {
				passwdResetReqFormSubmitHnd(connector).then((result) => {
					connector.messenger.clearErrors();
					passwdResetReqBox.style.display = 'none';
					document.querySelector('#signin-email').value = document.querySelector('#password-rst-req-email').value;
					document.querySelector('#signin-passwd').value = '';
					document.querySelector('#password-rst-req-email').value = '';
					signinBox.style.display = 'block';
				}, (reason) => {
					displayError(connector, reason);
				});
			});
		}
	}

	const passwdResetActBox = document.querySelector('.password-rst-act');

	if (router.orgId) {
		if (router.orgId === -1) {
			if (router.code) {
				if (passwdResetActBox) {
					passwdResetActBox.style.display = 'block';
					document.querySelector('#password-rst-act-email').value = router.email;
					document.querySelector('#password-rst-act-code').value = router.code;
					document.querySelector('#password-rst-act-passwd').value = '';
					document.querySelector('#password-rst-act-passwd2').value = '';
				}
			} else if (passwdResetReqBox) {
				passwdResetReqBoxShow();
			}
		} else {
			if (signinBox) {
				signinBox.style.display = 'block';
			}
		}
	} else {
		connector.messenger.postError('Bad URL. Sorry...');
	}

	const signInFormSubmitBtn = document.querySelector('#signin-form-submit-btn');
	if (signInFormSubmitBtn) {
		signInFormSubmitBtn.addEventListener('click', () => {
			signInHnd(connector).then((result) => {
				connector.messenger.clearErrors();
				signinBox.style.display = 'none';

				if (result.passwd_exp) {
					connector.token = null;

					document.querySelector('#password-rst-act-email').value = result.email;
					document.querySelector('#password-rst-act-code').value = result.code;
					document.querySelector('#password-rst-act-passwd').value = '';
					document.querySelector('#password-rst-act-passwd2').value = '';

					if (passwdResetActBox) {
						passwdResetActBox.style.display = 'block';
					}
				} else {
					connector.token = result.token;
					teamsLoadHnd(connector);
				}

			}, (reason) => {
				displayError(connector, reason);
			});
		});
	}

	const passwdResetReqFormSubmitHnd = (connector) => {
		const url = connector.router.getUrl('password/reset');
		return new Promise((resolve, reject) => {
			const xhr = new XMLHttpRequest();
			xhr.open('POST', url, true);
			xhr.setRequestHeader('Content-Type', 'application/json');
			xhr.onload = () => {
				const data = JSON.parse(xhr.responseText);
				if (xhr.status == 200) {
					resolve(data);
				} else {
					reject(data);
				}
			};
			xhr.onerror = () => {
				reject(xhr.statusText);
			};
			xhr.send(JSON.stringify({
				email: document.querySelector('#password-rst-req-email').value
			}));
		});
	};

	const passwdResetActFormSubmitHnd = (connector) => {
		const url = connector.router.getUrl('password/reset');
		return new Promise((resolve, reject) => {
			const xhr = new XMLHttpRequest();
			xhr.open('PATCH', url, true);
			xhr.setRequestHeader('Content-Type', 'application/json');
			xhr.onload = () => {
				const data = JSON.parse(xhr.responseText);
				if (xhr.status == 200) {
					resolve(data);
				} else {
					reject(data);
				}
			};
			xhr.onerror = () => {
				reject(xhr.statusText);
			};
			xhr.send(JSON.stringify({
				email: document.querySelector('#password-rst-act-email').value,
				code: document.querySelector('#password-rst-act-code').value,
				passwd1: document.querySelector('#password-rst-act-passwd').value,
				passwd2: document.querySelector('#password-rst-act-passwd2').value
			}));
		});
	};

	if (passwdResetActBox) {
		const passwdResetActSubmitBtn = document.querySelector('#password-rst-act-form-submit-btn');
		if (passwdResetActSubmitBtn) {
			passwdResetActSubmitBtn.addEventListener('click', () => {
				passwdResetActFormSubmitHnd(connector).then((result) => {
					connector.messenger.clearErrors();
					passwdResetActBox.style.display = 'none';
					router.setOrg(result.organization.id);
					document.querySelector('#signin-email').value = document.querySelector('#password-rst-act-email').value;
					document.querySelector('#signin-passwd').value = '';
					document.querySelector('#password-rst-act-email').value = '';
					document.querySelector('#password-rst-act-code').value = '';
					document.querySelector('#password-rst-act-passwd').value = '';
					document.querySelector('#password-rst-act-passwd2').value = '';
					signinBox.style.display = 'block';
				}, (reason) => {
					displayError(connector, reason);
				});
			});
		}
	}
});
