const { withAndroidManifest, withDangerousMod, withGradleProperties } = require('expo/config-plugins');
const fs = require('node:fs');
const path = require('node:path');

const domains = ['root', 'file', 'database', 'sharedpref', 'external', 'device_root', 'device_file', 'device_database', 'device_sharedpref'];
const excludes = domains.map(domain => `    <exclude domain="${domain}" path="." />`).join('\n');
const fullBackup = `<?xml version="1.0" encoding="utf-8"?>\n<full-backup-content>\n${excludes}\n</full-backup-content>\n`;
const extraction = `<?xml version="1.0" encoding="utf-8"?>\n<data-extraction-rules>\n  <cloud-backup>\n${excludes}\n  </cloud-backup>\n  <device-transfer>\n${excludes}\n  </device-transfer>\n</data-extraction-rules>\n`;

module.exports = function withLocalOnly(config) {
  config=withGradleProperties(config, config=>{
    const values={'org.gradle.jvmargs':'-Xmx1024m -XX:MaxMetaspaceSize=384m -XX:ActiveProcessorCount=2 -Xss512k -Dfile.encoding=UTF-8','org.gradle.parallel':'false','org.gradle.workers.max':'1','kotlin.compiler.execution.strategy':'in-process'};
    for(const [key,value] of Object.entries(values)){const existing=config.modResults.find(item=>item.type==='property'&&item.key===key);if(existing)existing.value=value;else config.modResults.push({type:'property',key,value});}
    return config;
  });
  config = withAndroidManifest(config, config => {
    const app = config.modResults.manifest.application[0].$;
    app['android:allowBackup'] = 'false';
    app['android:fullBackupContent'] = '@xml/backup_rules';
    app['android:dataExtractionRules'] = '@xml/data_extraction_rules';
    return config;
  });
  return withDangerousMod(config, ['android', async config => {
    const directory = path.join(config.modRequest.platformProjectRoot, 'app/src/main/res/xml');
    fs.mkdirSync(directory, { recursive: true });
    fs.writeFileSync(path.join(directory, 'backup_rules.xml'), fullBackup);
    fs.writeFileSync(path.join(directory, 'data_extraction_rules.xml'), extraction);
    return config;
  }]);
};
