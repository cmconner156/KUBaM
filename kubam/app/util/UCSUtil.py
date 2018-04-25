from ucsmsdk.ucsexception import UcsException
from server import UCSServer
from network import UCSNet
from session import UCSSession
from flask import jsonify
from db import YamlDB
from config import Const


class UCSUtil(object):
    # Login to the UCSM
    @staticmethod
    def login():
        err, msg, config = YamlDB.open_config(Const.KUBAM_CFG)
        if err == 0:
            if "ucsm" in config and "credentials" in config["ucsm"]:
                creds = config["ucsm"]["credentials"]
                if "user" in creds and "password" in creds and "ip" in creds:
                    h, msg = UCSSession.login(creds["user"], creds["password"], creds["ip"])
                    if msg != "":
                        return 1, msg, ""
                    if h != "":
                        return 0, msg, h
                    return 1, msg, ""
                else:
                    msg = "kubam.yaml file does not include the user, password, and ip properties to login."
                    err = 1
            else:
                msg = "UCS Credentials have not been entered.  Please login to UCS to continue."
                err = 1
        return err, msg, ""

    # Logout from the the UCSM
    @staticmethod
    def logout(handle):
        UCSSession.logout(handle)

    # Check if the login was successful
    @staticmethod
    def not_logged_in(msg):
        if not msg:
            msg = "not logged in to UCS"
        return jsonify({'error': msg}), 401

    # create org should not have org- prepended to it.
    @staticmethod
    def create_org(handle, org):
        print "Creating Organization: %s" % org
        from ucsmsdk.mometa.org.OrgOrg import OrgOrg
        mo = OrgOrg(parent_mo_or_dn="org-root", name=org, descr="KUBAM org")
        handle.add_mo(mo, modify_present=True)
        try:
            handle.commit()
        except UcsException as err:
            if err.error_code == "103":
                print "\tOrganization already exists."
            else:
                return 1, err.error_descr
        return 0, ""

    # org should not have org-<name> prepended."
    @staticmethod
    def query_org(handle, org):
        print "Checking if org %s exists" % org
        obj = handle.query_dn("org-root/org-" + org)
        if not obj:
            print "Org %s does not exist" % org
            return False
        else:
            print "Org %s exists." % org
            return True

    # org should be passed with the org-<name> prepended to it.
    @staticmethod
    def delete_org(handle, org):
        print "Deleting Org %s" % org
        mo = handle.query_dn(org)
        try:
            handle.remove_mo(mo)
            handle.commit()
        except AttributeError:
            print "\talready deleted"

    def get_full_org(self, handle):
        err, msg, org = YamlDB.get_org(Const.KUBAM_CFG)
        if err != 0:
            return err, msg, org
        if org == "":
            org = "kubam"

        if org == "root":
            full_org = "org-root"
        else:
            full_org = "org-root/org-" + org

        if org != "root":
            err, msg = self.create_org(handle, org)
        return err, msg, full_org

    # Make the UCS configuration using the Kubam information.
    def make_ucs(self):
        err, msg, handle = self.login()
        if err != 0:
            return self.not_logged_in(msg)
        err, msg, full_org = self.get_full_org(handle)
        if err != 0:
            return err, msg

        err, msg, net_settings = YamlDB.get_ucs_network(Const.KUBAM_CFG)
        selected_vlan = ""
        if "vlan" in net_settings:
            selected_vlan = net_settings["vlan"]
        if selected_vlan == "":
            self.logout(handle)
            return 1, "No vlan selected in UCS configuration."

        err, msg = UCSNet.createKubeNetworking(handle, full_org, selected_vlan)
        if err != 0:
            self.logout(handle)
            return err, msg

        # get the selected servers, and hosts.
        err, msg, hosts = YamlDB.get_hosts(Const.KUBAM_CFG)
        err, msg, servers = YamlDB.get_ucs_servers(Const.KUBAM_CFG)
        err, msg, kubam_ip = YamlDB.get_kubam_ip(Const.KUBAM_CFG)

        err, msg = UCSServer.createServerResources(handle, full_org, hosts, servers, kubam_ip)
        if err != 0:
            self.logout(handle)
            return err, msg

        self.logout(handle)
        return err, msg
