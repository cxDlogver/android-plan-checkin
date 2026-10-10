const {withAppBuildGradle}=require('expo/config-plugins');
const marker='// plancheckin external release signing';
const setup=`${marker}
def plancheckinStore = System.getenv('PLANCHECKIN_KEYSTORE')
def plancheckinStorePassword = System.getenv('PLANCHECKIN_STORE_PASSWORD')
def plancheckinAlias = System.getenv('PLANCHECKIN_KEY_ALIAS')
def plancheckinKeyPassword = System.getenv('PLANCHECKIN_KEY_PASSWORD')
def plancheckinSigningReady = [plancheckinStore, plancheckinStorePassword, plancheckinAlias, plancheckinKeyPassword].every { it != null && !it.isEmpty() }
if (gradle.startParameter.taskNames.any { it.toLowerCase().contains('release') }) {
    if (!plancheckinSigningReady) throw new GradleException('Release signing environment is required; debug signing is not permitted.')
    def keyFile = file(plancheckinStore).canonicalFile
    def repository = rootDir.parentFile.canonicalFile
    if (!keyFile.isFile() || keyFile.path.startsWith(repository.path + File.separator)) throw new GradleException('Release keystore must exist outside the repository.')
}
`;
function signingSource(source){
  if(source.includes(marker))return source;
  if(!/signingConfigs\s*\{/.test(source)||!/release\s*\{[\s\S]*?signingConfig signingConfigs\.debug/.test(source))throw new Error('Unsupported generated Gradle signing template');
  return source.replace(/android\s*\{/,`${setup}\nandroid {`)
    .replace(/signingConfigs\s*\{/,`signingConfigs {
        release {
            if (plancheckinSigningReady) {
                storeFile file(plancheckinStore)
                storePassword plancheckinStorePassword
                keyAlias plancheckinAlias
                keyPassword plancheckinKeyPassword
            }
        }`)
    .replace(/(buildTypes\s*\{[\s\S]*?release\s*\{[\s\S]*?)signingConfig signingConfigs\.debug/,'$1signingConfig signingConfigs.release');
}
module.exports=function withReleaseSigning(config){return withAppBuildGradle(config,config=>{config.modResults.contents=signingSource(config.modResults.contents);return config;});};
module.exports.signingSource=signingSource;
