from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from network import UCSNet
from hosts import hosts
from monitor import monitor
from server import servers
from config import Const
from server import UCSServer
from session import UCSSession
from util import UCSUtil
from iso import IsoMaker
from db import YamlDB
from autoinstall import Builder
from aci import aci


app = Flask(__name__)
app.register_blueprint(hosts)
app.register_blueprint(monitor)
app.register_blueprint(servers)
CORS(app)


ucs = UCSUtil()


@app.route('/')
@cross_origin()
def index():
    """
    / basic test to see if site is up. 
    should return { 'status' : 'ok'}
    """
    return jsonify({'status': 'ok'})



@app.route(Const.API_ROOT2 + "/aci", methods=['GET', 'POST', 'PUT', 'DELETE'])
@cross_origin()
def aci_handler():
    if request.method == 'POST':
        j, rc = aci.create(request.json)
    elif request.method == 'PUT':
        j, rc = aci.update(request.json)
    elif request.method == 'DELETE':
        j, rc = aci.delete(request.json)
    else:
        j, rc = aci.list()
    return jsonify(j), rc
        

# determine if we have credentials stored or not. 
@app.route(Const.API_ROOT + "/session", methods=['GET'])
@cross_origin()
def get_creds():
    creds = {}
    err, msg, config = YamlDB.open_config(Const.KUBAM_CFG)
    if err == 0:
        if "ucsm" in config and "credentials" in config["ucsm"]:
            creds = config["ucsm"]["credentials"]
            if "user" in creds and "password" in creds and "ip" in creds:
                creds["password"] = "REDACTED"
                #app.logger.info(creds)
    return jsonify({'credentials': creds}), 200


# test with: curl -H "Content-Type: application/json" -X POST -d '{"credentials": {"user" : "admin", "password" : "cisco123", "server" : "172.28.225.163"}}' http://localhost/api/v1/session
# every call logs in and logs out. 
@app.route(Const.API_ROOT + "/session", methods=['POST'])
@cross_origin()
def create_creds():
    if not request.json:
        return jsonify({'error': 'expected credentials hash'}), 400
     
    credentials = {} 
    credentials['user'] = request.json['credentials']['user']
    credentials['password'] = request.json['credentials']['password']
    credentials['ip'] = request.json['credentials']['server']
    if credentials['ip'] == "":
        return jsonify({'error': "Please enter a valid UCSM IP address."}), 401
    #app.logger.info("starting login attempt to UCS.")
    h, err = UCSSession.login(credentials['user'], 
                              credentials['password'],
                              credentials['ip'])
    if h == "":
        return jsonify({'error': err}), 401
    # write datafile. 
    YamlDB.update_ucs_creds(Const.KUBAM_CFG, credentials)
    UCSSession.logout(h)
    return jsonify({'login': "success"}), 201

@app.route(Const.API_ROOT + "/session", methods=['DELETE'])
@cross_origin()
def delete_session():
    YamlDB.update_ucs_creds(Const.KUBAM_CFG, "")
    return jsonify({'logout': "success"})


#get the kubam ip address
@app.route(Const.API_ROOT + "/ip", methods=['GET'])
@cross_origin()
def get_kubam_ip():
    err, msg, ip = YamlDB.get_kubam_ip(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'kubam_ip' : ip}), 200

#update the kubam IP address
@app.route(Const.API_ROOT + "/ip", methods=['POST'])
@cross_origin()
def update_kubam_ip():
    if not request.json:
        return jsonify({'error': 'expected request with kubam_ip '}), 400
    if "kubam_ip" not in request.json:
        return jsonify({'error': 'expected request with kubam_ip '}), 400

    ip = request.json['kubam_ip']
    err, msg = YamlDB.update_kubam_ip(Const.KUBAM_CFG, ip)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'kubam_ip' : ip}), 201

# get the org
@app.route(Const.API_ROOT + "/org", methods=['GET'])
@cross_origin()
def get_org():
    err, msg, org = YamlDB.get_org(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'org' : org}), 200


#update the org
@app.route(Const.API_ROOT + "/org", methods=['POST'])
@cross_origin()
def update_ucs_org():
    if not request.json:
        return jsonify({'error': 'expected request with org'}), 400
    if "org" not in request.json:
        return jsonify({'error': 'expected request with org'}), 400

    org = request.json['org']
    err, msg = YamlDB.update_org(Const.KUBAM_CFG, org)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'org' : org}), 201

# get the proxy
@app.route(Const.API_ROOT + "/proxy", methods=['GET'])
@cross_origin()
def get_proxy():
    err, msg, keys = YamlDB.get_proxy(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'proxy' : keys}), 200


# update proxy
@app.route(Const.API_ROOT + "/proxy", methods=['POST'])
@cross_origin()
def update_proxy():
    if not request.json:
        return jsonify({'error': 'expected request with proxy '}), 400
    if "proxy" not in request.json:
        return jsonify({'error': 'expected request with proxy'}), 400

    proxy = request.json['proxy']
    err, msg = YamlDB.update_proxy(Const.KUBAM_CFG, proxy)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'proxy' : proxy}), 201


# get the public keys
@app.route(Const.API_ROOT + "/keys", methods=['GET'])
@cross_origin()
def get_public_keys():
    err, msg, keys = YamlDB.get_public_keys(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'keys' : keys}), 200


# update public keys
@app.route(Const.API_ROOT + "/keys", methods=['POST'])
@cross_origin()
def update_public_keys():
    if not request.json:
        return jsonify({'error': 'expected request with keys '}), 400
    if "keys" not in request.json:
        return jsonify({'error': 'expected request with keys '}), 400

    keys = request.json['keys']
    err, msg = YamlDB.update_public_keys(Const.KUBAM_CFG, keys)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'keys' : keys}), 201

    
# get the networks in the UCS. 
@app.route(Const.API_ROOT + "/networks", methods=['GET'])
@cross_origin()
def get_networks():
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    vlans = UCSNet.listVLANs(handle) 
    UCSUtil.logout(handle)
    err, msg, net_hash = YamlDB.get_network(Const.KUBAM_CFG)
    err, msg, net_settings = YamlDB.get_ucs_network(Const.KUBAM_CFG)
    selected_vlan = ""
    if "vlan" in net_settings:
        selected_vlan = net_settings["vlan"]
       
    return jsonify({'vlans': [{"name": vlan.name, "id": vlan.id, "selected": (vlan.name == selected_vlan)}  for vlan in vlans], 'network' : net_hash}), 200
                    

@app.route(Const.API_ROOT + "/networks/vlan", methods=['POST'])
@cross_origin()
def select_vlan():
    if not request.json:
        return jsonify({'error': 'expected hash of VLANs'}), 400
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    #app.logger.info("Request is: ")
    #app.logger.info(request)
    vlan = request.json['vlan']
    err, msg = YamlDB.update_ucs_network(Const.KUBAM_CFG, {"vlan": vlan})
    if err != 0:
        return jsonify({'error': msg}), 500
    # return the existing networks now with the new one chosen. 
    return get_networks()
    

@app.route(Const.API_ROOT + "/networks", methods=['POST'])
@cross_origin()
def update_networks():
    if not request.json:
        return jsonify({'error': 'expected hash of network settings'}), 400
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    #app.logger.info("request is")
    #app.logger.info(request.json)
    vlan = request.json['vlan']
    err, msg = YamlDB.update_ucs_network(Const.KUBAM_CFG, {"vlan": vlan})
    if err != 0:
        return jsonify({'error': msg}), 400
    network = request.json['network']
    err, msg = YamlDB.update_network(Const.KUBAM_CFG, network)
    if err != 0:
        return jsonify({'error': msg}), 400
    return get_networks()

    
# see if there are any selected servers in the database 
def servers_to_api(ucs_servers, dbServers):
    for i, real_server in enumerate(ucs_servers):
        if real_server["type"] == "blade":
            if "blades" in dbServers:
                for b in dbServers["blades"]:
                    b_parts = b.split("/")
                    if (    len(b_parts) == 2 and 
                            real_server["chassis_id"] == b_parts[0] and 
                            real_server["slot"] == b_parts[1]):
                        real_server["selected"] = True
                        ucs_servers[i] = real_server
        elif real_server["type"] == "rack":
            if "rack_servers" in dbServers:
                for s in dbServers["rack_servers"]:
                    if real_server["rack_id"] == s:
                        real_server["selected"] = True
                        ucs_servers[i] = real_server
    return ucs_servers


@app.route(Const.API_ROOT + "/servers", methods=['GET'])
@cross_origin()
def get_servers():
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    servers = UCSServer.list_servers(handle) 
    UCSUtil.logout(handle)
  
    # gets a hash of severs of form:    
    # {blades: ["1/1", "1/2",..], rack: ["6", "7"]}
    err, msg, dbServers = YamlDB.get_ucs_servers(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    servers = servers_to_api(servers, dbServers) 
    #app.logger.info("returninng servers...")
    #app.logger.info(servers)
    err, msg, hosts = YamlDB.get_hosts(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'servers': servers, 'hosts': hosts}), 200


# translates the json we get from the web interface to what we expect to put in 
# the database.
def servers_to_db(servers):
    # gets a server array list and gets the selected servers and
    # puts them in the database form
    server_pool = {}
    #app.logger.info(servers)
    for s in servers:
        if "selected" in s and s["selected"] == True:
            if s["type"] == "blade":
                if not "blades" in server_pool:
                    server_pool["blades"] = []
                b = "%s/%s" % (s["chassis_id"] , s["slot"])
                server_pool["blades"].append(b)
            elif s["type"] == "rack":
                if not "rack_servers" in server_pool:
                    server_pool["rack_servers"] = []
                server_pool["rack_servers"].append(s["rack_id"])
    return server_pool

@app.route(Const.API_ROOT + "/servers", methods=['POST'])
@cross_origin()
def select_servers():
    # make sure we got some data.
    if not request.json:
        return jsonify({'error': 'expected hash of servers'}), 400
    # make sure we can login
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    servers = request.json['servers']
    # we expect servers to be a hash of like:
    # {blades: ["1/1", "1/2",..], rack: ["6", "7"]}
    servers = servers_to_db(servers)
    if servers:
        err, msg = YamlDB.update_ucs_servers(Const.KUBAM_CFG, servers)
        if err != 0:
            return jsonify({'error': msg}), 400
    if "hosts" not in request.json:
        return get_servers()
    
    hosts = request.json['hosts']
    err, msg = YamlDB.update_hosts(Const.KUBAM_CFG, hosts)
    if err != 0:
        return jsonify({'error': msg}), 400
    
    # return the existing networks now with the new one chosen. 
    return get_servers()



# list ISO images.
@app.route(Const.API_ROOT + "/isos", methods=['GET'])
@cross_origin()
def get_isos():
    err, isos = IsoMaker.list_isos("/kubam")    
    if err != 0:
        return jsonify({'error': isos})
    return jsonify({'isos': isos}), 200

# make the boot ISO image of an ISO
# curl -H "Content-Type: application/json" -X POST -d '{"iso" : "Vmware-ESXi-6.5.0-4564106-Custom-Cisco-6.5.0.2.iso" }' http://localhost/api/v1/isos/boot
# curl -H "Content-Type: application/json" -X POST -d '{"iso" : "CentOS-7-x86_64-Minimal-1611.iso" }' http://localhost/api/v1/isos/boot
@app.route(Const.API_ROOT + "/isos/boot", methods=['POST'])
@cross_origin()
def mkboot_iso():
    # get the iso map
    err, msg, isos = YamlDB.get_iso_map(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({"error": msg}), 400
    if len(isos) == 0:
        return jsonify({"error": "No ISOS have been mapped.  Please map an ISO image with an OS"}), 400
    err, msg = IsoMaker.mkboot_iso(isos)
    if err != 0:
        return jsonify({"error": msg}), 400

    err, msg = Builder.deploy_server_images(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({"error": msg}), 400
    return jsonify({"status": "ok"}), 201
    

# get the capabilities of KUBAM
@app.route(Const.API_ROOT + "/catalog", methods=['GET'])
@cross_origin()
def get_catalog():
    catalog = Builder.catalog
    app.logger.info(catalog)
    return jsonify(catalog), 200


#map the iso images to os versions. 
@app.route(Const.API_ROOT + "/isos/map", methods=['GET'])
@cross_origin()
def get_iso_map():
    err, msg, isos = YamlDB.get_iso_map(Const.KUBAM_CFG)
    if err != 0:
        return jsonify({'error': msg}), 400
    return jsonify({'iso_map' : isos}), 200

# update iso to os map
@app.route(Const.API_ROOT + "/isos/map", methods=['POST'])
@cross_origin()
def update_iso_map():
    app.logger.info("request.json")
    app.logger.info(request.json)
    if not request.json:
        return jsonify({'error': 'expected request with iso_map '}), 400
    if "iso_map" not in request.json:
        return jsonify({'error': 'expected request with iso_map '}), 400

    isos = request.json['iso_map']
    err, msg = YamlDB.update_iso_map(Const.KUBAM_CFG, isos)
    if err != 0:
        return jsonify({'error': msg}), 400
    return get_iso_map()



# Make the server images
@app.route(Const.API_ROOT + "/servers/images", methods=['POST'])
@cross_origin()
def deploy_server_autoinstall_images():
    err, msg = Builder.deploy_server_images(Const.KUBAM_CFG)
    if not err == 0:
        return jsonify({"error": msg})
    return jsonify({"status": "ok"}), 201
    

@app.route(Const.API_ROOT + "/settings", methods=['POST'])
@cross_origin()
def update_settings():
    app.logger.info(request.json)
    if not request.json:
        return jsonify({'error': 'expected kubam_ip and keys in json request'}), 400
    if not "kubam_ip" in request.json:
        return jsonify({'error': 'Please enter the IP address of the kubam server'}), 400
    if not "keys" in request.json:
        return jsonify({'error': 'Please specify keys.  See documentation for how this should look: https://ciscoucs.github.io/kubam/docs/settings.'}), 400
    # proxy and org are not manditory.
    

    if "proxy" in request.json:
        proxy = request.json['proxy']
        err, msg = YamlDB.update_proxy(Const.KUBAM_CFG, proxy)
        if err != 0:
            return jsonify({'error': msg}), 400

    if "org" in request.json:
        org = request.json['org']
        err, msg = YamlDB.update_org(Const.KUBAM_CFG, org)
        if err != 0:
            return jsonify({'error': msg}), 400

    # update the kubam_IP if it is changed.     
    ip = request.json['kubam_ip']
    err, msg = YamlDB.update_kubam_ip(Const.KUBAM_CFG, ip)
    if err != 0:
        return jsonify({'error': msg}), 400

    # update the keys if changed. 
    keys = request.json['keys']
    app.logger.info(keys)
    err, msg = YamlDB.update_public_keys(Const.KUBAM_CFG, keys)
    if err != 0:
        return jsonify({'error': msg}), 400


    return jsonify({"status": "ok"}), 201

# the grand daddy of them all.  It is what deploys everything. 
@app.route(Const.API_ROOT + "/deploy", methods=['POST'])
@cross_origin()
def deploy():
    err, msg = ucs.make_ucs()
    if err != 0:
        return jsonify({'error': msg}), 400
   
    # now call the deployment!    
    return jsonify({"status": "ok"}), 201


# dangerous command!  Will undo everything!
@app.route(Const.API_ROOT + "/deploy", methods=['DELETE'])
@cross_origin()
def destroy():
    app.logger.info("Deleting deployment")
    err, msg, handle = UCSUtil.login()
    if err != 0: 
        return UCSUtil.not_logged_in(msg)
    err, msg, hosts = YamlDB.get_hosts(Const.KUBAM_CFG)
    if err != 0: 
        return jsonify({'error': msg}), 400
    if len(hosts) == 0:
        return jsonify({"status": "no servers deployed"}),  200
    err, msg, full_org = ucs.get_full_org(handle)
    if err != 0: 
        return err, msg
    
    err, msg = UCSServer.deleteServerResources(handle, full_org, hosts)
    if err != 0: 
        return jsonify({'error': msg}), 400
    err, msg = UCSNet.deleteKubeNetworking(handle, full_org )
    if err != 0: 
        return jsonify({'error': msg}), 400
    return jsonify({"status": "ok"}), 201


if __name__ == '__main__':
    app.run(debug=True)

